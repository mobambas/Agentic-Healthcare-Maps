"""Run Phase 3 trust-score calibration end-to-end.

- Fits IsotonicRegression on the 20-record calibration split.
- Wraps it in mapie's SplitConformalClassifier (LAC, alpha=0.10).
- Conformalizes on the same calibration split (sharing fit and conformalize
  sets is a known approximation at our 30-record scale; the 10-record
  held-out coverage is the honest validation signal).
- Halts non-zero if empirical coverage < 0.85 (the master prompt floor).
- Writes data/phase3_trust_scores.jsonl with calibrated per-capability
  prediction sets for every source_record_id in phase2_extractions.jsonl.
- Prints a per-capability table and a per-record summary.

Run:
    python eval/phase3_calibration.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.calibrate import (
    CalibratedTrustScorer,
    CoverageReport,
    fit_calibrator,
    load_synonym_to_canonical,
)
from agent.schemas.facility import FacilityClaim
from agent.trust_score import (
    badge_for_prediction,
    compute_iphs_alignment_component,
    compute_self_consistency_component,
    compute_source_completeness_component,
    raw_score_for_capability,
    summarize_iphs_alignment,
)
from agent.validator import CapabilityValidation

GOLD_PATH = ROOT / "data" / "gold_labels.jsonl"
EXTRACT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
VALIDATIONS_PATH = ROOT / "data" / "phase4_validations.jsonl"
OUT_PATH = ROOT / "data" / "phase3_trust_scores.jsonl"

COVERAGE_FLOOR = 0.85


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fmt_pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def render_prediction_set(prediction_set: list[str]) -> str:
    if not prediction_set:
        return "{}"
    if len(prediction_set) == 1:
        return f"{{{prediction_set[0]}}}"
    return "{claimed,not_claimed}"


def load_validations(path: Path) -> dict[str, list[CapabilityValidation]]:
    """Reconstruct CapabilityValidation lists from data/phase4_validations.jsonl.
    Returns an empty dict if the file is missing (Phase 3 baseline behavior)."""
    if not path.exists():
        return {}
    by_sid: dict[str, list[CapabilityValidation]] = {}
    for record in load_jsonl(path):
        sid = record["source_record_id"]
        by_sid[sid] = [
            CapabilityValidation(
                source_record_id=v["source_record_id"],
                capability_name=v["capability_name"],
                iphs_alignment_score=v["iphs_alignment_score"],
                violated_rules=list(v.get("violated_rules", [])),
                supporting_evidence=list(v.get("supporting_evidence", [])),
                reasoning=v.get("reasoning", ""),
            )
            for v in record.get("validations", [])
        ]
    return by_sid


def main() -> int:
    gold = {
        record["source_record_id"]: record["proposed_labels"]
        for record in load_jsonl(GOLD_PATH)
    }
    extractions = {record["source_record_id"]: record for record in load_jsonl(EXTRACT_PATH)}
    if not extractions:
        print(f"No extractions at {EXTRACT_PATH}", file=sys.stderr)
        return 1

    synonym_to_canonical = load_synonym_to_canonical()
    validations_by_sid = load_validations(VALIDATIONS_PATH)
    scorer, report = fit_calibrator(
        extractions, gold, synonym_to_canonical, validations_by_sid=validations_by_sid
    )

    using_validations = bool(validations_by_sid)
    print("Phase 3 calibration" + (" (with Phase 4 validator)" if using_validations else ""))
    print(f"  validations loaded: {len(validations_by_sid)}")
    print(f"  alpha = {report.alpha:.2f}   target coverage = {report.confidence_level:.2f}")
    print(
        f"  cal records = {report.n_cal_records}   cal caps = {report.n_cal_caps}   "
        f"label balance (neg/pos) = {report.cal_label_balance[0]}/{report.cal_label_balance[1]}"
    )
    print(
        f"  test records = {report.n_test_records}   test caps = {report.n_test_caps}   "
        f"label balance (neg/pos) = {report.test_label_balance[0]}/{report.test_label_balance[1]}"
    )
    print(f"  empirical coverage on held-out = {report.empirical_coverage:.4f}")
    print()

    if report.empirical_coverage < COVERAGE_FLOOR:
        print(
            f"!!! empirical coverage {report.empirical_coverage:.4f} < floor {COVERAGE_FLOOR}; "
            "stopping per master prompt before writing phase3_trust_scores.jsonl",
            file=sys.stderr,
        )
        return 2

    return _write_outputs(extractions, scorer, report, validations_by_sid)


def _write_outputs(
    extractions: dict[str, dict],
    scorer: CalibratedTrustScorer,
    report: CoverageReport,
    validations_by_sid: dict[str, list[CapabilityValidation]],
) -> int:
    cap_table_rows: list[tuple[str, str, bool, float, float, str, str]] = []
    record_rows: list[dict] = []

    for sid, extraction in extractions.items():
        claim = FacilityClaim.model_validate(extraction["claim"])
        comp = compute_source_completeness_component(claim)
        validations = validations_by_sid.get(sid, [])
        iphs_by_cap = compute_iphs_alignment_component(claim, validations)
        violated_by_cap = {v.capability_name: v.violated_rules for v in validations}
        iphs_summary = summarize_iphs_alignment(iphs_by_cap)
        sc = compute_self_consistency_component(claim.capabilities)

        raws = [
            raw_score_for_capability(cap, comp, iphs_by_cap.get(cap.name, 1.0))
            for cap in claim.capabilities
        ]
        prediction_sets, calibrated = scorer.predict_set_batch(raws)

        capability_payloads = []
        badge_counter: Counter[str] = Counter()
        for cap, raw, pset, cal in zip(claim.capabilities, raws, prediction_sets, calibrated):
            badge = badge_for_prediction(cap.claimed, pset)
            badge_counter[badge] += 1
            cap_iphs = iphs_by_cap.get(cap.name, 1.0)
            capability_payloads.append(
                {
                    "name": cap.name,
                    "claimed": cap.claimed,
                    "confidence_self_consistency": cap.confidence_self_consistency,
                    "iphs_alignment": round(cap_iphs, 4),
                    "violated_rule_ids": list(violated_by_cap.get(cap.name, [])),
                    "raw_score": round(raw, 4),
                    "calibrated_score": round(float(cal), 4),
                    "prediction_set": pset,
                    "badge": badge,
                }
            )
            cap_table_rows.append(
                (
                    sid,
                    cap.name,
                    cap.claimed,
                    raw,
                    float(cal),
                    render_prediction_set(pset),
                    badge,
                )
            )

        blended = (sc + comp + iphs_summary) / 3.0
        record_rows.append(
            {
                "source_record_id": sid,
                "facility_name": claim.facility_name,
                "self_consistency_component": round(sc, 4),
                "source_completeness_component": round(comp, 4),
                "iphs_alignment_component": round(iphs_summary, 4),
                "blended_score": round(blended, 4),
                "capability_scores": capability_payloads,
                "badge_counts": dict(badge_counter),
            }
        )

    OUT_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in record_rows),
        encoding="utf-8",
    )

    print(f"per-capability table ({len(cap_table_rows)} rows)")
    header = (
        f"{'source_record_id':<18} {'name':<38} "
        f"{'claim':>5} {'raw':>5} {'calib':>5} {'pred_set':<24} {'badge':<6}"
    )
    print(header)
    print("-" * len(header))
    for row in cap_table_rows:
        sid, name, claimed, raw, cal, pset_str, badge = row
        print(
            f"{sid:<18} {name[:38]:<38} "
            f"{str(claimed)[:5]:>5} {raw:>5.2f} {cal:>5.2f} {pset_str:<24} {badge:<6}"
        )

    print()
    print("per-record summary")
    summary_header = (
        f"{'source_record_id':<18} {'sc':>5} {'comp':>5} {'iphs':>5} "
        f"{'blend':>5} {'green':>5} {'yellow':>6} {'red':>4}"
    )
    print(summary_header)
    print("-" * len(summary_header))
    total_badges: Counter[str] = Counter()
    for record in record_rows:
        bc = record["badge_counts"]
        total_badges.update(bc)
        print(
            f"{record['source_record_id']:<18} "
            f"{record['self_consistency_component']:>5.2f} "
            f"{record['source_completeness_component']:>5.2f} "
            f"{record['iphs_alignment_component']:>5.2f} "
            f"{record['blended_score']:>5.2f} "
            f"{bc.get('green', 0):>5} {bc.get('yellow', 0):>6} {bc.get('red', 0):>4}"
        )

    print()
    print(
        f"badge totals: green={total_badges.get('green', 0)} "
        f"yellow={total_badges.get('yellow', 0)} red={total_badges.get('red', 0)}"
    )
    print(
        f"empirical coverage = {report.empirical_coverage:.4f}  "
        f"(target = {report.confidence_level:.2f}, floor = {COVERAGE_FLOOR:.2f})"
    )
    print(f"wrote {len(record_rows)} records to {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
