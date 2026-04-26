"""Run the IPHS validator over the existing extractions and report stats.

- Loads data/phase2_extractions.jsonl.
- Initializes ValidatorAgent from data/iphs_rules.yaml.
- For each FacilityClaim, computes per-capability validations.
- Writes data/phase4_validations.jsonl.
- Prints:
    - per-capability violation counts
    - alignment-score distribution
    - top 5 facilities by total rule violations
    - rules that fired zero times across the gold set
- Halts non-zero if any single rule fires on more than 50% of capabilities
  (the master prompt's stop condition: that signals the rule is too broad).

Run:
    python eval/phase4_validator.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.schemas.facility import FacilityClaim
from agent.validator import CapabilityValidation, ValidatorAgent

EXTRACT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
RULES_PATH = ROOT / "data" / "iphs_rules.yaml"
OUT_PATH = ROOT / "data" / "phase4_validations.jsonl"

OVERFIRE_FRACTION = 0.50


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    extractions = load_jsonl(EXTRACT_PATH)
    if not extractions:
        print(f"No extractions at {EXTRACT_PATH}", file=sys.stderr)
        return 1

    validator = ValidatorAgent.from_yaml(RULES_PATH)
    rule_ids = [rule["id"] for rule in validator.rules]

    rule_fire_counts: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()
    cap_violation_counts: list[tuple[str, str, int, float, list[str]]] = []
    facility_violation_totals: dict[str, int] = {}
    total_caps = 0
    caps_with_any_violation = 0

    output_records: list[dict] = []

    for record in extractions:
        sid = record["source_record_id"]
        claim = FacilityClaim.model_validate(record["claim"])
        validations = validator.validate_facility(claim)

        record_violations = 0
        validation_payloads: list[dict] = []
        for validation in validations:
            total_caps += 1
            if validation.violated_rules:
                caps_with_any_violation += 1
                record_violations += len(validation.violated_rules)
                for rule_id in validation.violated_rules:
                    rule_fire_counts[rule_id] += 1
            score_buckets[f"{validation.iphs_alignment_score:.2f}"] += 1
            cap_violation_counts.append(
                (
                    sid,
                    validation.capability_name,
                    len(validation.violated_rules),
                    validation.iphs_alignment_score,
                    validation.violated_rules,
                )
            )
            validation_payloads.append(asdict(validation))

        facility_violation_totals[sid] = record_violations

        output_records.append(
            {
                "source_record_id": sid,
                "facility_name": claim.facility_name,
                "iphs_equivalent_tier": claim.iphs_equivalent_tier,
                "validations": validation_payloads,
            }
        )

    OUT_PATH.write_text(
        "".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in output_records),
        encoding="utf-8",
    )

    print("Phase 4 IPHS validator run")
    print(f"  rules loaded: {len(rule_ids)}")
    print(f"  facilities validated: {len(extractions)}")
    print(f"  total capabilities: {total_caps}")
    print(
        f"  capabilities with >=1 rule violation: {caps_with_any_violation} "
        f"({caps_with_any_violation / total_caps:.1%})"
    )
    print()

    print("alignment-score distribution")
    print(f"  {'score':>6} {'count':>5}")
    for score in ("1.00", "0.75", "0.50", "0.25", "0.00"):
        print(f"  {score:>6} {score_buckets.get(score, 0):>5}")
    print()

    print("rule fire counts")
    print(f"  {'rule_id':<6} {'fires':>5} {'pct of caps':>11}")
    overfiring_rules: list[tuple[str, int]] = []
    zero_fire_rules: list[str] = []
    for rule_id in rule_ids:
        fires = rule_fire_counts.get(rule_id, 0)
        pct = fires / total_caps if total_caps else 0
        marker = ""
        if fires == 0:
            zero_fire_rules.append(rule_id)
            marker = "  (zero-fire — narrow trigger or no record exhibits it)"
        elif pct > OVERFIRE_FRACTION:
            overfiring_rules.append((rule_id, fires))
            marker = "  (OVERFIRE — exceeds 50% threshold)"
        print(f"  {rule_id:<6} {fires:>5}    {pct * 100:>5.1f}%{marker}")
    print()

    if zero_fire_rules:
        print(
            f"zero-fire rules ({len(zero_fire_rules)}): "
            + ", ".join(zero_fire_rules)
        )
        print()

    if overfiring_rules:
        print(
            "ERROR: the following rules each fired on more than "
            f"{OVERFIRE_FRACTION:.0%} of capabilities, which the master prompt "
            "treats as a halt-and-ask condition:",
            file=sys.stderr,
        )
        for rule_id, fires in overfiring_rules:
            print(f"  {rule_id}: {fires} / {total_caps}", file=sys.stderr)
        return 2

    print("top 5 facilities by total rule violations")
    print(f"  {'source_record_id':<18} {'violations':>10}  facility_name")
    top = sorted(
        facility_violation_totals.items(), key=lambda kv: kv[1], reverse=True
    )[:5]
    name_by_sid = {rec["source_record_id"]: rec["facility_name"] for rec in output_records}
    for sid, count in top:
        if count == 0:
            continue
        print(f"  {sid:<18} {count:>10}  {name_by_sid.get(sid, '')}")

    print()
    print(f"wrote {len(output_records)} records to {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
