"""Phase 2 extraction pipeline with self-consistency.

Run:
    python -m agent.extract                  # process all 30 gold records
    python -m agent.extract --limit 3        # smoke test
    python -m agent.extract --budget-usd 2.0 # hard cap on estimated spend

Outputs JSONL to data/phase2_extractions.jsonl. Resumable: rerunning skips
records already present in the output file.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import anthropic
import instructor
import mlflow
from dotenv import load_dotenv
from mlflow.entities import SpanType
from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from tqdm import tqdm

from agent.schemas.facility import (
    Capability,
    FacilityCategory,
    FacilityClaim,
    IphsEquivalentTier,
    build_source_record_id,
)

load_dotenv(ROOT / ".env")

GOLD_PATH = ROOT / "data" / "gold_labels.jsonl"
CSV_PATH = ROOT / "data" / "vf_facilities.csv"
OUTPUT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
VOCAB_PATH = ROOT / "data" / "capability_vocabulary.md"
ALIASES_PATH = ROOT / "data" / "capability_aliases.yaml"
PREVIEW_PATH = ROOT / "data" / "canonicalization_preview.md"

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
DEFAULT_MLFLOW_TRACKING_URI = f"sqlite:///{ROOT}/.mlflow/mlflow.db"
DEFAULT_MLFLOW_EXPERIMENT = "agentic-healthcare-maps"
N_SAMPLES = 5
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 2048
GROUNDING_THRESHOLD = 0.95
CONSISTENCY_THRESHOLD = 3
PHASE2_VOCAB_HEADER = "## Phase 2 Coined Terms"
PHASE2_CANONICAL_HEADER = "## Phase 2 Canonicalized"
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TODAY = date(2026, 4, 26)

PUBLIC_TOKEN_INDICATORS = ["phc", "chc", "aiims", "esi", "cghs"]
PUBLIC_PHRASE_INDICATORS = [
    "government",
    "district hospital",
    "sub-district hospital",
    "sub-centre",
]
NULLS = {"", "null", "none", "nan", "[]"}

INPUT_COST_PER_MTOK = 3.0
OUTPUT_COST_PER_MTOK = 15.0


def setup_mlflow(experiment: str | None = None) -> None:
    """Configure tracking URI + experiment + Anthropic autolog.

    Tracking URI defaults to a local SQLite store at .mlflow/mlflow.db; override
    via MLFLOW_TRACKING_URI for the eventual UC Delta target in Phase 8.
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_MLFLOW_TRACKING_URI)
    if tracking_uri.startswith("sqlite:"):
        db_path = Path(tracking_uri.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment or os.getenv("MLFLOW_EXPERIMENT", DEFAULT_MLFLOW_EXPERIMENT))
    # Autolog must be called explicitly: mlflow does not enable it by default
    # in serverless environments per the master prompt.
    mlflow.anthropic.autolog()


class CapabilityExtraction(BaseModel):
    """LLM-only fields per capability. Server-side merged into Capability."""

    name: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    claimed: bool
    evidence_quote: str = Field(..., min_length=1, max_length=400)
    iphs_equivalent_tier: IphsEquivalentTier | None = None


class FacilityExtraction(BaseModel):
    """LLM output. Combined with row metadata to build a FacilityClaim."""

    reasoning: str = Field(default="", max_length=600)
    facility_category: FacilityCategory
    iphs_equivalent_tier: IphsEquivalentTier | None = None
    capabilities: list[CapabilityExtraction] = Field(default_factory=list, max_length=20)


def is_present(value: object) -> bool:
    return value is not None and str(value).strip().lower() not in NULLS


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def parse_listish(value: object) -> list[str]:
    text = norm(value)
    if not is_present(text):
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return [text]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if is_present(item)]
    return [text]


def text_for_field(row: dict[str, str], field: str) -> str:
    if field == "description":
        return norm(row.get(field)) if is_present(row.get(field)) else ""
    return " | ".join(parse_listish(row.get(field)))


def build_source_text(row: dict[str, str]) -> str:
    fields = ["description", "specialties", "procedure", "equipment", "capability"]
    return "\n\n".join(f"<{field}>\n{text_for_field(row, field)}\n</{field}>" for field in fields)


def has_public_signal(row: dict[str, str], source_text: str) -> bool:
    if norm(row.get("operatorTypeId")).lower() == "public":
        return True
    lowered = source_text.lower()
    if any(phrase in lowered for phrase in PUBLIC_PHRASE_INDICATORS):
        return True
    return any(re.search(rf"\b{token}\b", lowered) for token in PUBLIC_TOKEN_INDICATORS)


def _extract_vocab_terms(text: str) -> list[str]:
    return [match.group(1) for match in re.finditer(r"^- `([a-z][a-z0-9_]*)`", text, flags=re.MULTILINE)]


def parse_vocab_sections(text: str) -> tuple[list[str], list[str]]:
    """Split vocab markdown into (pre_phase2_terms, phase2_terms)."""
    if PHASE2_VOCAB_HEADER not in text:
        return _extract_vocab_terms(text), []
    pre, post = text.split(PHASE2_VOCAB_HEADER, 1)
    return _extract_vocab_terms(pre), _extract_vocab_terms(post)


def load_vocab() -> set[str]:
    if not VOCAB_PATH.exists():
        return set()
    return set(_extract_vocab_terms(VOCAB_PATH.read_text(encoding="utf-8")))


def load_aliases(path: Path = ALIASES_PATH) -> dict[str, list[str]]:
    """Load the flat YAML alias map: top-level keys are canonical names, values are synonym lists."""
    if not path.exists():
        return {}
    import yaml

    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {canonical: list(synonyms or []) for canonical, synonyms in data.items()}


def build_synonym_to_canonical(aliases: dict[str, list[str]]) -> dict[str, str]:
    reverse: dict[str, str] = {}
    for canonical, synonyms in aliases.items():
        for synonym in synonyms:
            if synonym in reverse and reverse[synonym] != canonical:
                raise ValueError(
                    f"alias conflict: {synonym} maps to both {reverse[synonym]} and {canonical}"
                )
            reverse[synonym] = canonical
    return reverse


def append_new_vocab(new_terms: list[str]) -> None:
    if not new_terms:
        return
    text = VOCAB_PATH.read_text(encoding="utf-8")
    if "## Phase 2 Coined Terms" not in text:
        text = text.rstrip() + "\n\n## Phase 2 Coined Terms\n\n"
    for term in sorted(set(new_terms)):
        line = f"- `{term}`\n"
        if line not in text:
            text += line
    VOCAB_PATH.write_text(text, encoding="utf-8")


def make_system_prompt(vocab: set[str]) -> str:
    vocab_lines = "\n".join(f"- {term}" for term in sorted(vocab))
    return f"""You extract structured capability claims from messy Indian healthcare facility records.

The source text uses XML-style tags: <description>, <specialties>, <procedure>, <equipment>, <capability>.

For each distinct capability the source claims, return:
- name: snake_case identifier matching ^[a-z][a-z0-9_]*$. Prefer the controlled vocabulary listed below; coin a new snake_case name ONLY when no controlled term fits.
- claimed: true if the source asserts the capability.
- evidence_quote: a verbatim substring of the source text. Do not paraphrase. Do not add or remove words.
- iphs_equivalent_tier: one of {{shc_hwc, phc, chc_non_fru, chc_fru, sdh_dh}} ONLY if the source text contains an explicit public-sector indicator (operatorTypeId="public", or any of: government, PHC, CHC, district hospital, sub-district hospital, sub-centre, AIIMS, ESI, CGHS). Otherwise null.

For the facility as a whole, return:
- facility_category: one of hospital, clinic, dental, pharmacy, diagnostic, single_practitioner, other.
- iphs_equivalent_tier: same rule as above; default null.
- reasoning: a short note on category and tier choice. Keep under 200 characters.

Do not invent capabilities not present in the source. Do not produce capabilities for administrative metadata such as incorporation dates, ISIC codes, payment methods, or location-only or status-only assertions.

CONTROLLED VOCABULARY (prefer these; coin new only if none fit):
{vocab_lines}
- <specialty>_services for declared specialty values normalized to snake_case (e.g. cardiology_services, dermatology_services)."""


def make_user_message(row: dict[str, str], source_text: str, source_id: str) -> str:
    return f"""source_record_id: {source_id}
facility_name: {norm(row.get('name'))}
operatorTypeId: {norm(row.get('operatorTypeId')) or 'null'}
facilityTypeId: {norm(row.get('facilityTypeId')) or 'null'}
state: {norm(row.get('address_stateOrRegion')) or 'null'}

Source text (extract evidence_quote substrings ONLY from below):
{source_text}"""


@mlflow.trace(span_type=SpanType.TOOL, name="ground_capability")
def ground_capability(cap: CapabilityExtraction, source_text: str) -> tuple[str, tuple[int, int]] | None:
    quote = cap.evidence_quote.strip()
    if not quote:
        return None
    idx = source_text.find(quote)
    if idx >= 0:
        return quote, (idx, idx + len(quote))
    alignment = fuzz.partial_ratio_alignment(quote, source_text)
    if alignment is None or alignment.score / 100.0 < GROUNDING_THRESHOLD:
        return None
    grounded_quote = source_text[alignment.dest_start : alignment.dest_end]
    if not grounded_quote.strip():
        return None
    return grounded_quote, (alignment.dest_start, alignment.dest_end)


def int_or_none(value: object) -> int | None:
    if not is_present(value):
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def days_since(value: object) -> int | None:
    if not is_present(value):
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(str(value).strip(), fmt).date()
            return max(0, (TODAY - parsed).days)
        except ValueError:
            continue
    return None


def compute_completeness(row: dict[str, str]) -> float:
    cols = [
        "name",
        "officialPhone",
        "officialWebsite",
        "address_zipOrPostcode",
        "description",
        "specialties",
        "procedure",
        "equipment",
        "capability",
        "latitude",
        "longitude",
    ]
    return round(sum(1 for col in cols if is_present(row.get(col))) / len(cols), 4)


def build_claim(
    extraction: FacilityExtraction,
    row: dict[str, str],
    source_text: str,
    source_id: str,
) -> tuple[FacilityClaim, int]:
    rejections = 0
    grounded_caps: list[Capability] = []
    seen_names: set[str] = set()
    facility_has_public = has_public_signal(row, source_text)
    enforced_facility_tier = extraction.iphs_equivalent_tier if facility_has_public else None

    for cap in extraction.capabilities:
        if not SNAKE_CASE_RE.match(cap.name):
            rejections += 1
            continue
        if cap.name in seen_names:
            continue
        grounded = ground_capability(cap, source_text)
        if grounded is None:
            rejections += 1
            continue
        quote, offsets = grounded
        cap_tier = cap.iphs_equivalent_tier if facility_has_public else None
        try:
            grounded_caps.append(
                Capability(
                    name=cap.name,
                    claimed=cap.claimed,
                    evidence_quote=quote,
                    evidence_char_offset=offsets,
                    confidence_self_consistency=1.0,
                    iphs_equivalent_tier=cap_tier,
                    iphs_rule_violations=[],
                )
            )
        except Exception:
            rejections += 1
            continue
        seen_names.add(cap.name)

    claim = FacilityClaim(
        source_record_id=source_id,
        facility_name=norm(row.get("name")),
        facility_category=extraction.facility_category,
        iphs_equivalent_tier=enforced_facility_tier,
        capabilities=grounded_caps,
        data_completeness_score=compute_completeness(row),
        has_official_phone=is_present(row.get("officialPhone")),
        has_official_website=is_present(row.get("officialWebsite")),
        social_media_presence_count=int_or_none(row.get("distinct_social_media_presence_count")) or 0,
        days_since_last_update=days_since(row.get("recency_of_page_update")),
        declared_doctor_count=int_or_none(row.get("numberDoctors")),
        declared_capacity=int_or_none(row.get("capacity")),
    )
    return claim, rejections


def aggregate_claims(claims: list[FacilityClaim]) -> FacilityClaim:
    if not claims:
        raise ValueError("No claims to aggregate")

    cap_groups: dict[str, list[Capability]] = {}
    for claim in claims:
        seen_in_sample: set[str] = set()
        for cap in claim.capabilities:
            if cap.name in seen_in_sample:
                continue
            seen_in_sample.add(cap.name)
            cap_groups.setdefault(cap.name, []).append(cap)

    kept: list[Capability] = []
    for name, instances in cap_groups.items():
        if len(instances) < CONSISTENCY_THRESHOLD:
            continue
        quote_counter = Counter(cap.evidence_quote for cap in instances)
        modal_quote = quote_counter.most_common(1)[0][0]
        chosen = next(cap for cap in instances if cap.evidence_quote == modal_quote)
        tier_counter = Counter(cap.iphs_equivalent_tier for cap in instances)
        modal_tier = tier_counter.most_common(1)[0][0]
        kept.append(
            Capability(
                name=name,
                claimed=chosen.claimed,
                evidence_quote=chosen.evidence_quote,
                evidence_char_offset=chosen.evidence_char_offset,
                confidence_self_consistency=len(instances) / N_SAMPLES,
                iphs_equivalent_tier=modal_tier,
                iphs_rule_violations=[],
            )
        )

    category = Counter(c.facility_category for c in claims).most_common(1)[0][0]
    tier = Counter(c.iphs_equivalent_tier for c in claims).most_common(1)[0][0]
    base = claims[0]
    return base.model_copy(update={
        "facility_category": category,
        "iphs_equivalent_tier": tier,
        "capabilities": kept,
    })


def estimate_call_cost(system_prompt: str, user_message: str, raw_response: object | None) -> float:
    """Cost estimate. Uses Anthropic usage if available; otherwise rough char-based."""
    if raw_response is not None and hasattr(raw_response, "usage"):
        usage = raw_response.usage
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        billable_input = input_tokens + cache_write * 1.25 + cache_read * 0.10
        return (billable_input * INPUT_COST_PER_MTOK + output_tokens * OUTPUT_COST_PER_MTOK) / 1_000_000
    estimated_input = (len(system_prompt) + len(user_message)) / 4
    estimated_output = 800
    return (estimated_input * INPUT_COST_PER_MTOK + estimated_output * OUTPUT_COST_PER_MTOK) / 1_000_000


@mlflow.trace(span_type=SpanType.LLM, name="anthropic_extract_call")
def call_model(
    client: instructor.Instructor,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float,
) -> tuple[FacilityExtraction | None, object | None]:
    try:
        result, raw = client.messages.create_with_completion(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_message}],
            response_model=FacilityExtraction,
            temperature=temperature,
            max_retries=2,
        )
        return result, raw
    except Exception as exc:
        print(f"  call failed: {exc}", file=sys.stderr)
        return None, None


@mlflow.trace(span_type=SpanType.CHAIN, name="process_facility")
def process_facility(
    client: instructor.Instructor,
    model: str,
    system_prompt: str,
    user_message: str,
    source_text: str,
    source_id: str,
    row: dict[str, str],
    *,
    n_samples: int = N_SAMPLES,
    temperature: float = TEMPERATURE,
    budget_remaining: float = float("inf"),
) -> tuple[list[FacilityClaim], int, float, bool]:
    """Run N sample extractions for one facility and return raw claims.

    Returns (sample_claims, sample_rejection_total, cost_used, budget_hit).
    Aggregation and canonicalization happen in the caller — this function is
    the trace boundary for one record's pipeline.
    """
    mlflow.update_current_trace(
        tags={"source_record_id": source_id, "model": model}
    )
    sample_claims: list[FacilityClaim] = []
    sample_rejections = 0
    cost_used = 0.0
    for _ in range(n_samples):
        if cost_used > budget_remaining:
            return sample_claims, sample_rejections, cost_used, True
        result, raw = call_model(client, model, system_prompt, user_message, temperature)
        cost_used += estimate_call_cost(system_prompt, user_message, raw)
        if result is None:
            continue
        claim, rej = build_claim(result, row, source_text, source_id)
        sample_claims.append(claim)
        sample_rejections += rej
    return sample_claims, sample_rejections, cost_used, False


def load_existing_extractions() -> dict[str, dict]:
    if not OUTPUT_PATH.exists():
        return {}
    out: dict[str, dict] = {}
    for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[rec["source_record_id"]] = rec
    return out


def _validate_aliases_against_vocab(
    aliases: dict[str, list[str]], vocab: set[str]
) -> list[str]:
    issues = []
    for canonical in aliases:
        if canonical not in vocab:
            issues.append(f"canonical '{canonical}' is not in capability_vocabulary.md")
    return issues


def canonicalize_existing(apply: bool = False) -> int:
    """Drive alias-map canonicalization on data/phase2_extractions.jsonl.

    Default mode: preview only. Writes canonicalization_preview.md. Does NOT
    modify the JSONL or vocabulary file.

    With apply=True: rewrites JSONL with canonical names (deduping by max
    confidence within each record), removes canonicalized synonyms from the
    Phase 2 Coined Terms vocab section, and appends any names that survive
    in the JSONL but are not in the alias map and not in the vocabulary
    under the Phase 2 Canonicalized header.
    """
    if not OUTPUT_PATH.exists():
        print(f"No extractions file at {OUTPUT_PATH}", file=sys.stderr)
        return 1
    if not VOCAB_PATH.exists():
        print(f"No vocabulary file at {VOCAB_PATH}", file=sys.stderr)
        return 1
    if not ALIASES_PATH.exists():
        print(f"No alias map at {ALIASES_PATH}", file=sys.stderr)
        return 1

    aliases = load_aliases(ALIASES_PATH)
    vocab = load_vocab()
    issues = _validate_aliases_against_vocab(aliases, vocab)
    if issues:
        for issue in issues:
            print(f"alias-map error: {issue}", file=sys.stderr)
        return 1

    synonym_to_canonical = build_synonym_to_canonical(aliases)

    records: list[dict] = []
    for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))

    renames_by_pair: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for record in records:
        sid = record["source_record_id"]
        for cap in record["claim"]["capabilities"]:
            canonical = synonym_to_canonical.get(cap["name"])
            if canonical is None or canonical == cap["name"]:
                continue
            renames_by_pair.setdefault((cap["name"], canonical), []).append(
                (sid, cap["evidence_quote"])
            )

    preview_lines = [
        "# Canonicalization Preview",
        "",
        f"Source: `{OUTPUT_PATH.relative_to(ROOT)}`",
        f"Alias map: `{ALIASES_PATH.relative_to(ROOT)}`",
        "",
        f"Total renames that would fire: {sum(len(v) for v in renames_by_pair.values())} "
        f"({len(renames_by_pair)} distinct pairs).",
        "",
    ]
    if not renames_by_pair:
        preview_lines.append("No renames would fire on the current JSONL.")
    else:
        for (synonym, canonical), occurrences in sorted(renames_by_pair.items()):
            preview_lines.append(f"## `{synonym}` -> `{canonical}`  ({len(occurrences)} cap{'s' if len(occurrences) != 1 else ''})")
            preview_lines.append("")
            for sid, evidence in occurrences:
                preview_lines.append(f"- `{sid}`  evidence_quote: {evidence!r}")
            preview_lines.append("")

    PREVIEW_PATH.write_text("\n".join(preview_lines).rstrip() + "\n", encoding="utf-8")

    if not apply:
        print(f"Preview written to {PREVIEW_PATH}", file=sys.stderr)
        print(
            f"{sum(len(v) for v in renames_by_pair.values())} caps would be renamed across "
            f"{len(renames_by_pair)} pairs. Re-run with --apply to commit.",
            file=sys.stderr,
        )
        return 0

    rewritten = 0
    for record in records:
        merged: dict[str, dict] = {}
        for cap in record["claim"]["capabilities"]:
            new_name = synonym_to_canonical.get(cap["name"], cap["name"])
            cap_dict = dict(cap)
            cap_dict["name"] = new_name
            existing = merged.get(new_name)
            if existing is None:
                merged[new_name] = cap_dict
            elif cap_dict["confidence_self_consistency"] > existing["confidence_self_consistency"]:
                merged[new_name] = cap_dict
            if new_name != cap["name"]:
                rewritten += 1
        record["claim"]["capabilities"] = list(merged.values())

    OUTPUT_PATH.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )

    aliased_synonyms = set(synonym_to_canonical.keys())
    vocab_text = VOCAB_PATH.read_text(encoding="utf-8")
    if PHASE2_VOCAB_HEADER in vocab_text:
        prefix, _, post = vocab_text.partition(PHASE2_VOCAB_HEADER)
        surviving = sorted(
            term
            for term in _extract_vocab_terms(post)
            if term not in aliased_synonyms
        )
        body = "\n".join(f"- `{term}`" for term in surviving) if surviving else ""
        rebuilt = f"{prefix.rstrip()}\n\n{PHASE2_VOCAB_HEADER}\n\n{body}\n".rstrip() + "\n"
        VOCAB_PATH.write_text(rebuilt, encoding="utf-8")

    survivors_in_jsonl = {
        cap["name"]
        for record in records
        for cap in record["claim"]["capabilities"]
    }
    refreshed_vocab = load_vocab()
    new_terms = sorted(
        name
        for name in survivors_in_jsonl
        if name not in refreshed_vocab and name not in aliased_synonyms
    )
    if new_terms:
        vocab_text = VOCAB_PATH.read_text(encoding="utf-8")
        if PHASE2_CANONICAL_HEADER not in vocab_text:
            vocab_text = vocab_text.rstrip() + f"\n\n{PHASE2_CANONICAL_HEADER}\n\n"
        for term in new_terms:
            line = f"- `{term}`\n"
            if line not in vocab_text:
                vocab_text += line
        VOCAB_PATH.write_text(vocab_text, encoding="utf-8")

    print(
        f"Applied {rewritten} renames across {len(records)} records. "
        f"New terms appended under {PHASE2_CANONICAL_HEADER}: {len(new_terms)}.",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--budget-usd", type=float, default=2.0)
    parser.add_argument(
        "--canonicalize-existing",
        action="store_true",
        help="Run alias-map canonicalizer on existing JSONL + vocab. No API calls. "
        "Writes a preview by default; pass --apply to commit changes.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="With --canonicalize-existing, actually rewrite the JSONL and vocab "
        "instead of only writing the preview.",
    )
    args = parser.parse_args()

    if args.canonicalize_existing:
        return canonicalize_existing(apply=args.apply)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment or .env", file=sys.stderr)
        return 1

    setup_mlflow()
    vocab = load_vocab()
    print(f"Loaded vocabulary: {len(vocab)} terms", file=sys.stderr)
    print(f"MLflow tracking: {mlflow.get_tracking_uri()}", file=sys.stderr)

    gold_records = [
        json.loads(line)
        for line in GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows_by_id = {
            build_source_record_id(
                row.get("name"),
                row.get("address_zipOrPostcode"),
                row.get("latitude"),
                row.get("longitude"),
            ): row
            for row in csv.DictReader(handle)
        }

    if args.limit:
        gold_records = gold_records[: args.limit]

    existing = load_existing_extractions()
    todo = [r for r in gold_records if r["source_record_id"] not in existing]
    print(
        f"To process: {len(todo)} / {len(gold_records)} records (existing: {len(existing)}). Model: {args.model}",
        file=sys.stderr,
    )

    client = instructor.from_anthropic(anthropic.Anthropic())
    system_prompt = make_system_prompt(vocab)

    total_cost = 0.0
    new_vocab: list[str] = []
    budget_hit = False

    with OUTPUT_PATH.open("a", encoding="utf-8") as out_handle:
        for gold_record in tqdm(todo, desc="records"):
            source_id = gold_record["source_record_id"]
            row = rows_by_id.get(source_id)
            if row is None:
                print(f"  warning: no CSV row for {source_id}", file=sys.stderr)
                continue
            source_text = build_source_text(row)
            user_message = make_user_message(row, source_text, source_id)

            sample_claims, sample_rejections, cost_used, record_budget_hit = process_facility(
                client,
                args.model,
                system_prompt,
                user_message,
                source_text,
                source_id,
                row,
                budget_remaining=args.budget_usd - total_cost,
            )
            total_cost += cost_used
            if record_budget_hit:
                budget_hit = True
                print(f"BUDGET EXCEEDED at ${total_cost:.2f}; stopping early", file=sys.stderr)
                break

            if not sample_claims:
                print(f"  no successful samples for {source_id}", file=sys.stderr)
                continue

            aggregated = aggregate_claims(sample_claims)
            for cap in aggregated.capabilities:
                if cap.name not in vocab and cap.name not in new_vocab:
                    new_vocab.append(cap.name)
            record_out = {
                "source_record_id": source_id,
                "claim": aggregated.model_dump(),
                "rejection_count": sample_rejections,
                "n_samples_succeeded": len(sample_claims),
                "n_samples_target": N_SAMPLES,
                "model": args.model,
            }
            out_handle.write(json.dumps(record_out, ensure_ascii=False) + "\n")
            out_handle.flush()

    append_new_vocab(new_vocab)
    print(f"\nNew vocabulary terms appended: {len(set(new_vocab))}", file=sys.stderr)
    print(f"Estimated total cost: ${total_cost:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
