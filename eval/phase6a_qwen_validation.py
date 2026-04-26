"""Compare the Qwen 2.5 7B Instruct (vLLM) extraction against the Sonnet 4.6
reference set on the 30-record gold dataset.

Inputs:
    data/gold_labels.jsonl                          (human-verified labels)
    data/phase2_extractions.jsonl                   (Sonnet 4.6 reference)
    data/phase6a_qwen_validation.jsonl              (Qwen 2.5 7B output)
    data/capability_aliases.yaml                    (canonicalization map)

Outputs (stdout):
    Per-record: capability recall + precision against gold (canonicalized).
    Per-record: agreement rate between Qwen and Sonnet (Jaccard on cap names).
    Aggregate: recall, precision, Sonnet-Qwen agreement.
    List: caps Sonnet caught but Qwen missed (gold-confirmed only).
    List: caps Qwen caught but Sonnet missed (gold-confirmed only).

Halt condition (master prompt): if aggregate Qwen recall < 0.75, exit 2 — the
calling notebook should stop before launching the full 10K extraction.

Run:
    python eval/phase6a_qwen_validation.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold_labels.jsonl"
SONNET_PATH = ROOT / "data" / "phase2_extractions.jsonl"
QWEN_PATH = ROOT / "data" / "phase6a_qwen_validation.jsonl"
ALIASES_PATH = ROOT / "data" / "capability_aliases.yaml"

RECALL_FLOOR = 0.75


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_synonym_to_canonical(path: Path) -> dict[str, str]:
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


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def main() -> int:
    gold_records = load_jsonl(GOLD_PATH)
    if not gold_records:
        print(f"missing {GOLD_PATH}", file=sys.stderr)
        return 1
    sonnet_records = {r["source_record_id"]: r for r in load_jsonl(SONNET_PATH)}
    qwen_records = {r["source_record_id"]: r for r in load_jsonl(QWEN_PATH)}
    if not qwen_records:
        print(f"missing {QWEN_PATH}; run agent.extract_open against the gold set first.", file=sys.stderr)
        return 1

    synonym_to_canonical = load_synonym_to_canonical(ALIASES_PATH)
    print(
        f"alias map synonyms loaded: {len(synonym_to_canonical)}",
        file=sys.stderr,
    )

    rows = []
    sonnet_caught_qwen_missed: Counter[str] = Counter()
    qwen_caught_sonnet_missed: Counter[str] = Counter()
    for gold in gold_records:
        sid = gold["source_record_id"]
        gold_names = canonicalize(
            {cap["name"] for cap in gold["proposed_labels"]["capabilities"]},
            synonym_to_canonical,
        )
        sonnet_rec = sonnet_records.get(sid)
        qwen_rec = qwen_records.get(sid)
        sonnet_names = canonicalize(
            {cap["name"] for cap in sonnet_rec["claim"]["capabilities"]} if sonnet_rec else set(),
            synonym_to_canonical,
        )
        qwen_names = canonicalize(
            {cap["name"] for cap in qwen_rec["claim"]["capabilities"]} if qwen_rec else set(),
            synonym_to_canonical,
        )
        qwen_recall = (
            len(gold_names & qwen_names) / len(gold_names) if gold_names else 1.0
        )
        qwen_precision = (
            len(gold_names & qwen_names) / len(qwen_names) if qwen_names else 1.0
        )
        sonnet_recall = (
            len(gold_names & sonnet_names) / len(gold_names) if gold_names else 1.0
        )
        # Caps gold-confirmed in one model but missing in the other
        sonnet_only = (gold_names & sonnet_names) - qwen_names
        qwen_only = (gold_names & qwen_names) - sonnet_names
        for name in sonnet_only:
            sonnet_caught_qwen_missed[name] += 1
        for name in qwen_only:
            qwen_caught_sonnet_missed[name] += 1

        rows.append(
            {
                "sid": sid,
                "n_gold": len(gold_names),
                "n_sonnet": len(sonnet_names),
                "n_qwen": len(qwen_names),
                "qwen_recall": qwen_recall,
                "qwen_precision": qwen_precision,
                "sonnet_recall": sonnet_recall,
                "sonnet_qwen_jaccard": jaccard(sonnet_names, qwen_names),
                "qwen_present": qwen_rec is not None,
                "sonnet_present": sonnet_rec is not None,
            }
        )

    print()
    print(
        f"{'source_record_id':<18} "
        f"{'gold':>4} {'son':>4} {'qwn':>4} "
        f"{'qwn_R':>6} {'qwn_P':>6} {'son_R':>6} {'jaccard':>7}"
    )
    print("-" * 68)
    for r in rows:
        marker = "" if r["qwen_present"] else "  ⚠ qwen missing"
        print(
            f"{r['sid']:<18} "
            f"{r['n_gold']:>4} {r['n_sonnet']:>4} {r['n_qwen']:>4} "
            f"{r['qwen_recall']:>6.2f} {r['qwen_precision']:>6.2f} "
            f"{r['sonnet_recall']:>6.2f} {r['sonnet_qwen_jaccard']:>7.2f}"
            f"{marker}"
        )

    valid = [r for r in rows if r["qwen_present"]]
    if not valid:
        print("no qwen records present; cannot compute aggregates", file=sys.stderr)
        return 1

    avg_qwen_recall = sum(r["qwen_recall"] for r in valid) / len(valid)
    avg_qwen_precision = sum(r["qwen_precision"] for r in valid) / len(valid)
    avg_sonnet_recall = sum(r["sonnet_recall"] for r in valid) / len(valid)
    avg_jaccard = sum(r["sonnet_qwen_jaccard"] for r in valid) / len(valid)

    print()
    print(f"aggregate over {len(valid)} qwen-covered records:")
    print(f"  Qwen recall vs gold:    {avg_qwen_recall:.3f}")
    print(f"  Qwen precision vs gold: {avg_qwen_precision:.3f}")
    print(f"  Sonnet recall vs gold:  {avg_sonnet_recall:.3f}  (reference)")
    print(f"  Sonnet–Qwen Jaccard:    {avg_jaccard:.3f}")

    print()
    print("top capabilities Sonnet caught but Qwen missed (gold-confirmed):")
    for name, count in sonnet_caught_qwen_missed.most_common(15):
        print(f"  {count:>3}  {name}")
    if not sonnet_caught_qwen_missed:
        print("  (none)")

    print()
    print("top capabilities Qwen caught but Sonnet missed (gold-confirmed):")
    for name, count in qwen_caught_sonnet_missed.most_common(15):
        print(f"  {count:>3}  {name}")
    if not qwen_caught_sonnet_missed:
        print("  (none)")

    print()
    if avg_qwen_recall < RECALL_FLOOR:
        print(
            f"!!! Qwen recall {avg_qwen_recall:.3f} < floor {RECALL_FLOOR}; "
            "halt before full 10K extraction (master prompt directive)",
            file=sys.stderr,
        )
        return 2
    print(
        f"OK — Qwen recall {avg_qwen_recall:.3f} ≥ floor {RECALL_FLOOR}. "
        "Cleared to launch full 10K extraction."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
