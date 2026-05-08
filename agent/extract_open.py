"""Phase 6 open-weight extraction module.

Mirrors `agent.extract` but routes the structured-extraction LLM call to a
vLLM-served, OpenAI-compatible endpoint hosting Qwen 2.5 7B Instruct (or any
other instruct-tuned open model). Same Pydantic schema, same prompt, same
self-consistency aggregation, same evidence-grounding rejection.

Why a parallel module: the Sonnet 4.6 30-record reference set in
`data/phase2_extractions.jsonl` is a comparison artifact for the demo. We do
not modify the Sonnet path while iterating on the open-weight path.

CLI:
    python -m agent.extract_open                                    # full CSV → data/phase6_extractions_qwen.jsonl
    python -m agent.extract_open --records-from data/gold_labels.jsonl \\
                                 --output data/phase6a_qwen_validation.jsonl
    python -m agent.extract_open --limit 5                          # quick smoke test
    python -m agent.extract_open --endpoint-url http://1.2.3.4:8000/v1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import instructor
import mlflow
import openai
from dotenv import load_dotenv
from mlflow.entities import SpanType
from tqdm import tqdm

from agent.extract import (
    CSV_PATH,
    GOLD_PATH,
    MAX_OUTPUT_TOKENS,
    N_SAMPLES,
    TEMPERATURE,
    FacilityClaim,
    FacilityExtraction,
    aggregate_claims,
    build_claim,
    build_source_record_id,
    build_source_text,
    load_vocab,
    make_system_prompt,
    make_user_message,
    setup_mlflow,
)

load_dotenv(ROOT / ".env")

DEFAULT_OUTPUT_PATH = ROOT / "data" / "phase6_extractions_qwen.jsonl"
DEFAULT_VLLM_ENDPOINT_URL = os.getenv("VLLM_ENDPOINT_URL", "http://localhost:8000/v1")
DEFAULT_QWEN_MODEL = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")
DEFAULT_VLLM_API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")

# Open-weight max_tokens override. The Sonnet path uses 2048 because Anthropic
# tool calling overhead is small. For Qwen via vLLM, instructor's JSON-mode
# retry cycle re-includes the previous failed output as prompt context, which
# can push input + max_tokens above vLLM's --max-model-len 4096 ceiling. 1024
# tokens of output is comfortably above the Phase 2 average of ~600 and leaves
# room for retries.
QWEN_MAX_OUTPUT_TOKENS = 1024


def make_client(endpoint_url: str, api_key: str = DEFAULT_VLLM_API_KEY) -> instructor.Instructor:
    """Build an instructor-wrapped OpenAI client pointed at the vLLM endpoint.

    Uses instructor.Mode.JSON_SCHEMA, which sends the Pydantic schema in
    OpenAI's `response_format={"type": "json_schema", ...}` field. vLLM honors
    this with grammar-constrained decoding at the token level, preventing the
    "model echoes the schema document instead of producing an instance"
    failure that Mode.JSON exhibits on smaller open-weight models.
    """
    base = openai.OpenAI(base_url=endpoint_url, api_key=api_key, timeout=180.0)
    return instructor.from_openai(base, mode=instructor.Mode.JSON_SCHEMA)


@mlflow.trace(span_type=SpanType.LLM, name="qwen_extract_call")
def call_model(
    client: instructor.Instructor,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float,
) -> tuple[FacilityExtraction | None, Any]:
    """One sample call against the vLLM endpoint via Instructor + JSON_SCHEMA mode."""
    try:
        result, raw = client.chat.completions.create_with_completion(
            model=model,
            max_tokens=QWEN_MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_model=FacilityExtraction,
            temperature=temperature,
            max_retries=2,
        )
        return result, raw
    except Exception as exc:
        print(f"  call failed: {exc}", file=sys.stderr)
        return None, None


def temperature_schedule(sample_index: int) -> float:
    """Sample 0 deterministic (temp 0.0); samples 1..N at TEMPERATURE for variance."""
    return 0.0 if sample_index == 0 else TEMPERATURE


@mlflow.trace(span_type=SpanType.CHAIN, name="process_facility_qwen")
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
) -> tuple[list[FacilityClaim], int]:
    """Run N sample extractions for one facility and return raw claims."""
    mlflow.update_current_trace(
        tags={"source_record_id": source_id, "model": model, "provider": "vllm-openai"}
    )
    sample_claims: list[FacilityClaim] = []
    sample_rejections = 0
    for index in range(n_samples):
        temp = temperature_schedule(index)
        result, _ = call_model(client, model, system_prompt, user_message, temp)
        if result is None:
            continue
        claim, rej = build_claim(result, row, source_text, source_id)
        sample_claims.append(claim)
        sample_rejections += rej
    return sample_claims, sample_rejections


def load_filter_ids(path: Path) -> set[str] | None:
    if not path or not path.exists():
        return None
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        ids.add(record["source_record_id"])
    return ids


def load_existing_extractions(output_path: Path) -> dict[str, dict]:
    if not output_path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out[record["source_record_id"]] = record
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_QWEN_MODEL)
    parser.add_argument("--endpoint-url", default=DEFAULT_VLLM_ENDPOINT_URL)
    parser.add_argument(
        "--records-from",
        default=None,
        help="Optional JSONL file whose source_record_id values define the input set "
        "(e.g. data/gold_labels.jsonl for a validation pass). Default: process every CSV row.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Output JSONL path. Default: {DEFAULT_OUTPUT_PATH.relative_to(ROOT)}.",
    )
    parser.add_argument("--n-samples", type=int, default=N_SAMPLES)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    setup_mlflow()
    print(f"MLflow tracking: {mlflow.get_tracking_uri()}", file=sys.stderr)
    print(f"vLLM endpoint:   {args.endpoint_url}", file=sys.stderr)
    print(f"Model:           {args.model}", file=sys.stderr)

    vocab = load_vocab()
    print(f"vocabulary terms loaded: {len(vocab)}", file=sys.stderr)

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows_by_id = {
        build_source_record_id(
            row.get("name"),
            row.get("address_zipOrPostcode"),
            row.get("latitude"),
            row.get("longitude"),
        ): row
        for row in rows
    }

    filter_path = Path(args.records_from).resolve() if args.records_from else None
    filter_ids = load_filter_ids(filter_path) if filter_path else None
    if filter_ids is not None:
        print(
            f"filtering to {len(filter_ids)} ids from {filter_path.relative_to(ROOT)}",
            file=sys.stderr,
        )
        target_ids = [sid for sid in rows_by_id.keys() if sid in filter_ids]
    else:
        target_ids = list(rows_by_id.keys())

    if args.limit is not None:
        target_ids = target_ids[: args.limit]

    existing = load_existing_extractions(output_path)
    todo = [sid for sid in target_ids if sid not in existing]
    print(
        f"to process: {len(todo)} / {len(target_ids)} records "
        f"(existing: {len(existing)})",
        file=sys.stderr,
    )

    if not todo:
        print("nothing to do.", file=sys.stderr)
        return 0

    client = make_client(args.endpoint_url)
    system_prompt = make_system_prompt(vocab)

    samples_failed = 0
    with output_path.open("a", encoding="utf-8") as out_handle:
        for source_id in tqdm(todo, desc="records"):
            row = rows_by_id.get(source_id)
            if row is None:
                continue
            source_text = build_source_text(row)
            user_message = make_user_message(row, source_text, source_id)

            sample_claims, sample_rejections = process_facility(
                client,
                args.model,
                system_prompt,
                user_message,
                source_text,
                source_id,
                row,
                n_samples=args.n_samples,
            )
            if not sample_claims:
                samples_failed += 1
                print(f"  no successful samples for {source_id}", file=sys.stderr)
                continue

            aggregated = aggregate_claims(sample_claims)
            record_out = {
                "source_record_id": source_id,
                "claim": aggregated.model_dump(),
                "rejection_count": sample_rejections,
                "n_samples_succeeded": len(sample_claims),
                "n_samples_target": args.n_samples,
                "model": args.model,
                "provider": "vllm-openai-compatible",
            }
            out_handle.write(json.dumps(record_out, ensure_ascii=False) + "\n")
            out_handle.flush()

    if samples_failed:
        print(
            f"warning: {samples_failed} records produced zero successful samples", file=sys.stderr
        )
    print(f"wrote to {output_path.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
