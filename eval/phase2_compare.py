"""Compare Phase 2 extractions against the human-verified gold labels.

The alias map at data/capability_aliases.yaml is applied to BOTH gold and
extracted capability names before set comparison so that synonym/canonical
naming differences do not penalize precision or recall. Files on disk are
not modified by this eval.

Run:
    python eval/phase2_compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold_labels.jsonl"
EXTRACT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
ALIASES_PATH = ROOT / "data" / "capability_aliases.yaml"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_synonym_to_canonical(path: Path) -> dict[str, str]:
    """Load the flat YAML alias map and flatten into a synonym->canonical lookup."""
    if not path.exists():
        return {}
    import yaml

    with path.open(encoding="utf-8") as fh:
        aliases = yaml.safe_load(fh) or {}
    reverse: dict[str, str] = {}
    for canonical, synonyms in aliases.items():
        for synonym in synonyms or []:
            reverse[synonym] = canonical
    return reverse


def canonicalize(names: set[str], synonym_to_canonical: dict[str, str]) -> set[str]:
    return {synonym_to_canonical.get(name, name) for name in names}


def main() -> int:
    gold_records = load_jsonl(GOLD_PATH)
    gold = {r["source_record_id"]: r["proposed_labels"] for r in gold_records}
    gold_meta = {r["source_record_id"]: r for r in gold_records}
    extractions = {r["source_record_id"]: r for r in load_jsonl(EXTRACT_PATH)}

    if not extractions:
        print(f"No extractions found at {EXTRACT_PATH}", file=sys.stderr)
        return 1

    synonym_to_canonical = load_synonym_to_canonical(ALIASES_PATH)
    print(
        f"Loaded {len(synonym_to_canonical)} synonyms from {ALIASES_PATH.name}; "
        f"applied to both gold and extracted names.",
        file=sys.stderr,
    )

    rows = []
    for sid, gold_claim in gold.items():
        if sid not in extractions:
            rows.append({"sid": sid, "missing": True})
            continue
        record = extractions[sid]
        ext_claim = record["claim"]
        gold_names = canonicalize(
            {cap["name"] for cap in gold_claim["capabilities"]}, synonym_to_canonical
        )
        ext_names = canonicalize(
            {cap["name"] for cap in ext_claim["capabilities"]}, synonym_to_canonical
        )
        true_positives = len(gold_names & ext_names)
        recall = true_positives / len(gold_names) if gold_names else 1.0
        precision = true_positives / len(ext_names) if ext_names else 1.0
        ext_category = ext_claim["facility_category"]
        gold_category = gold_claim["facility_category"]
        alternates = gold_meta[sid].get("category_alternates", []) or []
        category_match = ext_category == gold_category or ext_category in alternates
        rows.append({
            "sid": sid,
            "missing": False,
            "n_gold": len(gold_names),
            "n_ext": len(ext_names),
            "tp": true_positives,
            "recall": recall,
            "precision": precision,
            "category_match": category_match,
            "rejections": record.get("rejection_count", 0),
            "n_samples": record.get("n_samples_succeeded", 0),
        })

    print(f"{'source_record_id':<18} {'gold':>5} {'ext':>5} {'tp':>4} {'recall':>7} {'prec':>6} {'cat':>5} {'rej':>4} {'n':>3}")
    print("-" * 76)
    for row in rows:
        if row.get("missing"):
            print(f"{row['sid']:<18} MISSING")
            continue
        print(
            f"{row['sid']:<18} "
            f"{row['n_gold']:>5} {row['n_ext']:>5} {row['tp']:>4} "
            f"{row['recall']:>7.2f} {row['precision']:>6.2f} "
            f"{str(row['category_match'])[:5]:>5} "
            f"{row['rejections']:>4} {row['n_samples']:>3}"
        )

    valid = [row for row in rows if not row.get("missing")]
    if not valid:
        return 0
    avg_recall = sum(r["recall"] for r in valid) / len(valid)
    avg_precision = sum(r["precision"] for r in valid) / len(valid)
    cat_acc = sum(1 for r in valid if r["category_match"]) / len(valid)
    total_rej = sum(r["rejections"] for r in valid)
    print()
    print(f"Aggregate over {len(valid)} records:")
    print(f"  capability recall:    {avg_recall:.3f}")
    print(f"  capability precision: {avg_precision:.3f}")
    print(f"  category accuracy:    {cat_acc:.3f}")
    print(f"  evidence rejections:  {total_rej} (total across all samples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
