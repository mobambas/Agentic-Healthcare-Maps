"""Run Phase 2–5 eval scripts in sequence, aggregate metrics, write dashboard + JSON.

Usage:
    python eval/run_all.py
    python eval/run_all.py --since-last-run

Writes:
    artifacts/eval/metrics.json
    artifacts/eval/dashboard.html
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
ARTIFACTS_DIR = ROOT / "artifacts" / "eval"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
DASHBOARD_PATH = ARTIFACTS_DIR / "dashboard.html"


def _max_mtime(paths: list[Path]) -> float:
    mtimes: list[float] = []
    for p in paths:
        if p.exists():
            mtimes.append(p.stat().st_mtime)
    return max(mtimes) if mtimes else 0.0


def _agent_py_files() -> list[Path]:
    agent_root = ROOT / "agent"
    if not agent_root.is_dir():
        return []
    return sorted(agent_root.rglob("*.py"))


def _phase_dependencies(phase_id: str) -> list[Path]:
    """Files whose mtimes should invalidate a cached result for --since-last-run."""
    script_names = {
        "phase2": "phase2_compare.py",
        "phase3": "phase3_calibration.py",
        "phase4": "phase4_validator.py",
        "phase5": "phase5_trace_check.py",
    }
    script = EVAL_DIR / script_names[phase_id]
    out: list[Path] = [script]

    if phase_id == "phase2":
        out += [
            ROOT / "data" / "gold_labels.jsonl",
            ROOT / "data" / "phase2_extractions.jsonl",
            ROOT / "data" / "capability_aliases.yaml",
        ]
    elif phase_id == "phase3":
        out += [
            ROOT / "data" / "gold_labels.jsonl",
            ROOT / "data" / "phase2_extractions.jsonl",
        ]
        vpath = ROOT / "data" / "phase4_validations.jsonl"
        if vpath.exists():
            out.append(vpath)
        out.extend(_agent_py_files())
    elif phase_id == "phase4":
        out += [
            ROOT / "data" / "phase2_extractions.jsonl",
            ROOT / "data" / "iphs_rules.yaml",
        ]
        out.extend(_agent_py_files())
    elif phase_id == "phase5":
        out += [
            ROOT / "data" / "vf_facilities.csv",
        ]
        out.extend(_agent_py_files())

    return out


@dataclass
class PhaseResult:
    phase_id: str
    display_name: str
    exit_code: int
    stdout: str
    stderr: str
    skipped: bool = False
    last_executed_at: str = ""
    headline_metrics: dict[str, Any] = field(default_factory=dict)
    halt: dict[str, Any] = field(
        default_factory=lambda: {"triggered": False, "reason": None}
    )


def _run_script(rel_script: str) -> tuple[int, str, str]:
    cmd = [sys.executable, str(ROOT / rel_script)]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _parse_phase2(stdout: str, stderr: str, exit_code: int) -> PhaseResult:
    r = PhaseResult(
        phase_id="phase2",
        display_name="Phase 2 — extraction vs gold",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )
    recall_m = re.search(r"capability recall:\s+([\d.]+)", stdout)
    prec_m = re.search(r"capability precision:\s+([\d.]+)", stdout)
    cat_m = re.search(r"category accuracy:\s+([\d.]+)", stdout)
    rej_m = re.search(r"evidence rejections:\s+(\d+)", stdout)
    n_m = re.search(r"Aggregate over (\d+) records", stdout)
    if recall_m:
        r.headline_metrics["avg_capability_recall"] = float(recall_m.group(1))
    if prec_m:
        r.headline_metrics["avg_capability_precision"] = float(prec_m.group(1))
    if cat_m:
        r.headline_metrics["category_accuracy"] = float(cat_m.group(1))
    if rej_m:
        r.headline_metrics["evidence_rejections_total"] = int(rej_m.group(1))
    if n_m:
        r.headline_metrics["records_in_aggregate"] = int(n_m.group(1))
    if exit_code != 0:
        r.halt = {"triggered": True, "reason": f"exit_code_{exit_code}"}
        if "No extractions found" in stderr:
            r.halt["reason"] = "missing_extractions"
    return r


def _parse_phase3(stdout: str, stderr: str, exit_code: int) -> PhaseResult:
    r = PhaseResult(
        phase_id="phase3",
        display_name="Phase 3 — trust calibration",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )
    held_m = re.search(r"empirical coverage on held-out = ([\d.]+)", stdout)
    if held_m:
        r.headline_metrics["empirical_coverage_held_out"] = float(held_m.group(1))
    emp_m = re.search(
        r"empirical coverage = ([\d.]+)\s+\(target = ([\d.]+), floor = ([\d.]+)\)",
        stdout,
    )
    if emp_m:
        r.headline_metrics["empirical_coverage"] = float(emp_m.group(1))
        r.headline_metrics["target_coverage"] = float(emp_m.group(2))
        r.headline_metrics["coverage_floor"] = float(emp_m.group(3))
    alpha_m = re.search(r"alpha = ([\d.]+)\s+target coverage = ([\d.]+)", stdout)
    if alpha_m and "target_coverage" not in r.headline_metrics:
        r.headline_metrics["alpha"] = float(alpha_m.group(1))
        r.headline_metrics["target_coverage"] = float(alpha_m.group(2))
    val_m = re.search(r"validations loaded: (\d+)", stdout)
    if val_m:
        r.headline_metrics["validations_loaded_records"] = int(val_m.group(1))
    badge_m = re.search(
        r"badge totals: green=(\d+)\s+yellow=(\d+)\s+red=(\d+)", stdout
    )
    if badge_m:
        r.headline_metrics["badges_green"] = int(badge_m.group(1))
        r.headline_metrics["badges_yellow"] = int(badge_m.group(2))
        r.headline_metrics["badges_red"] = int(badge_m.group(3))

    halt_reason = None
    if exit_code == 2:
        halt_reason = "empirical_coverage_below_floor"
    if "empirical coverage" in stderr and "floor" in stderr:
        halt_reason = "empirical_coverage_below_floor"
    if halt_reason:
        r.halt = {"triggered": True, "reason": halt_reason}
    elif exit_code != 0:
        r.halt = {"triggered": True, "reason": f"exit_code_{exit_code}"}
    return r


def _parse_phase4(stdout: str, stderr: str, exit_code: int) -> PhaseResult:
    r = PhaseResult(
        phase_id="phase4",
        display_name="Phase 4 — IPHS validator",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )
    rules_m = re.search(r"rules loaded: (\d+)", stdout)
    fac_m = re.search(r"facilities validated: (\d+)", stdout)
    caps_m = re.search(r"total capabilities: (\d+)", stdout)
    viol_m = re.search(
        r"capabilities with >=1 rule violation: (\d+) \(([\d.]+)%\)", stdout
    )
    if rules_m:
        r.headline_metrics["rules_loaded"] = int(rules_m.group(1))
    if fac_m:
        r.headline_metrics["facilities_validated"] = int(fac_m.group(1))
    if caps_m:
        r.headline_metrics["total_capabilities"] = int(caps_m.group(1))
    if viol_m:
        r.headline_metrics["caps_with_violation"] = int(viol_m.group(1))
        r.headline_metrics["caps_with_violation_pct"] = float(viol_m.group(2))

    halt_reason = None
    if exit_code == 2 and "OVERFIRE" in stdout:
        halt_reason = "rule_overfire_gt_50pct"
    if exit_code == 2 and stderr and "halt" in stderr.lower():
        halt_reason = "rule_overfire_gt_50pct"
    if halt_reason:
        r.halt = {"triggered": True, "reason": halt_reason}
    elif exit_code != 0:
        r.halt = {"triggered": True, "reason": f"exit_code_{exit_code}"}
    return r


def _parse_phase5(stdout: str, stderr: str, exit_code: int) -> PhaseResult:
    r = PhaseResult(
        phase_id="phase5",
        display_name="Phase 5 — MLflow trace check",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )
    counts_m = re.search(
        r"span counts: LLM=(\d+)\s+CHAT_MODEL=(\d+)\s+TOOL=(\d+)\s+"
        r"AGENT=(\d+)\s+RETRIEVER=(\d+)",
        stdout,
    )
    if counts_m:
        r.headline_metrics["llm_spans"] = int(counts_m.group(1))
        r.headline_metrics["chat_model_spans"] = int(counts_m.group(2))
        r.headline_metrics["tool_spans"] = int(counts_m.group(3))
        r.headline_metrics["agent_spans"] = int(counts_m.group(4))
        r.headline_metrics["retriever_spans"] = int(counts_m.group(5))
    types_m = re.search(r"distinct span_types observed: (\[[^\]]+\])", stdout)
    if types_m:
        r.headline_metrics["span_types_observed"] = types_m.group(1)

    r.headline_metrics["trace_contract_ok"] = "OK — trace satisfies" in stdout

    halt_reason = None
    if exit_code == 2 and "FAILURES:" in stdout:
        halt_reason = "trace_contract_failures"
    if exit_code == 1 and "ANTHROPIC_API_KEY" in stderr:
        halt_reason = "missing_api_key"
    if halt_reason:
        r.halt = {"triggered": True, "reason": halt_reason}
    elif exit_code != 0:
        r.halt = {"triggered": True, "reason": f"exit_code_{exit_code}"}
    return r


PARSERS = {
    "phase2": _parse_phase2,
    "phase3": _parse_phase3,
    "phase4": _parse_phase4,
    "phase5": _parse_phase5,
}

RUN_ORDER: list[tuple[str, str]] = [
    ("phase2", "eval/phase2_compare.py"),
    ("phase3", "eval/phase3_calibration.py"),
    ("phase4", "eval/phase4_validator.py"),
    ("phase5", "eval/phase5_trace_check.py"),
]


def _result_from_cached(phase_id: str, blob: dict[str, Any]) -> PhaseResult:
    display_names = {
        "phase2": "Phase 2 — extraction vs gold",
        "phase3": "Phase 3 — trust calibration",
        "phase4": "Phase 4 — IPHS validator",
        "phase5": "Phase 5 — MLflow trace check",
    }
    lea = str(blob.get("last_executed_at") or "")
    return PhaseResult(
        phase_id=phase_id,
        display_name=display_names[phase_id],
        exit_code=int(blob.get("exit_code", -1)),
        stdout=str(blob.get("stdout", "")),
        stderr=str(blob.get("stderr", "")),
        skipped=True,
        last_executed_at=lea,
        headline_metrics=dict(blob.get("headline_metrics", {})),
        halt=dict(blob.get("halt", {"triggered": False, "reason": None})),
    )


def _load_previous_metrics() -> dict[str, Any] | None:
    if not METRICS_PATH.exists():
        return None
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _should_skip_phase(
    phase_id: str,
    since_last_run: bool,
    baseline_ts: float,
    previous: dict[str, Any] | None,
) -> bool:
    if not since_last_run or previous is None:
        return False
    phases = previous.get("phases") or {}
    if phase_id not in phases:
        return False
    deps_max = _max_mtime(_phase_dependencies(phase_id))
    if deps_max > baseline_ts:
        return False
    return True


def _build_dashboard(generated_at: str, results: list[PhaseResult]) -> str:
    sections: list[str] = []
    for pr in results:
        metrics_rows = "".join(
            f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(json.dumps(v))}</td></tr>"
            for k, v in pr.headline_metrics.items()
        )
        halt_cls = "halt-yes" if pr.halt.get("triggered") else "halt-no"
        halt_txt = (
            f"Halt: yes — {html.escape(str(pr.halt.get('reason')))}"
            if pr.halt.get("triggered")
            else "Halt: no"
        )
        skip_note = (
            '<p class="skipped">Used cached result (--since-last-run).</p>'
            if pr.skipped
            else ""
        )
        run_at = pr.last_executed_at or generated_at
        out_preview = (pr.stdout + "\n" + pr.stderr)[-8000:]
        sections.append(
            f"""
<section class="phase" id="{html.escape(pr.phase_id)}">
  <h2>{html.escape(pr.display_name)}</h2>
  <p class="meta">Eval last run: <strong>{html.escape(run_at)}</strong> (UTC). Dashboard generated: {html.escape(generated_at)}.</p>
  {skip_note}
  <p class="{halt_cls}"><strong>{halt_txt}</strong></p>
  <p>Exit code: {pr.exit_code}</p>
  <h3>Headline metrics</h3>
  <table class="metrics">
    <tbody>{metrics_rows or '<tr><td colspan="2"><em>No metrics parsed</em></td></tr>'}</tbody>
  </table>
  <h3>Output (tail)</h3>
  <pre class="log">{html.escape(out_preview)}</pre>
</section>
"""
        )

    css = """
    body { font-family: system-ui, sans-serif; margin: 2rem; max-width: 960px; color: #1a1a1a; }
    h1 { font-size: 1.5rem; }
    .phase { border: 1px solid #ccc; border-radius: 8px; padding: 1rem 1.25rem; margin: 1.5rem 0; background: #fafafa; }
    .meta { color: #555; font-size: 0.9rem; }
    .halt-yes { color: #b00020; }
    .halt-no { color: #1b5e20; }
    .skipped { color: #6a4c00; font-style: italic; }
    table.metrics { border-collapse: collapse; width: 100%; }
    table.metrics th, table.metrics td { border: 1px solid #ddd; padding: 0.35rem 0.5rem; text-align: left; }
    table.metrics th { background: #eee; width: 40%; }
    pre.log { background: #111; color: #e0e0e0; padding: 1rem; overflow-x: auto; font-size: 0.75rem; max-height: 24rem; }
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Eval dashboard — Phases 2–5</title>
  <style>{css}</style>
</head>
<body>
  <h1>Eval dashboard — Phases 2–5</h1>
  <p>Generated <strong>{html.escape(generated_at)}</strong> (UTC).</p>
  {"".join(sections)}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since-last-run",
        action="store_true",
        help="Skip phases whose dependency files are older than metrics.json timestamp.",
    )
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    previous = _load_previous_metrics() if args.since_last_run else None
    baseline_ts = 0.0
    if previous and args.since_last_run:
        raw_ts = previous.get("generated_at")
        if isinstance(raw_ts, str):
            try:
                baseline_ts = datetime.fromisoformat(
                    raw_ts.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                baseline_ts = 0.0

    results: list[PhaseResult] = []
    phases_out: dict[str, Any] = {}

    for phase_id, script_path in RUN_ORDER:
        prev_blob = (previous or {}).get("phases", {}).get(phase_id, {})
        if _should_skip_phase(phase_id, args.since_last_run, baseline_ts, previous):
            pr = _result_from_cached(phase_id, prev_blob)
            if not pr.last_executed_at:
                pr.last_executed_at = str(
                    prev_blob.get("last_executed_at")
                    or (previous.get("generated_at") if previous else "")
                )
            results.append(pr)
        else:
            exit_code, stdout, stderr = _run_script(script_path)
            pr = PARSERS[phase_id](stdout, stderr, exit_code)
            pr.last_executed_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            results.append(pr)

        phases_out[phase_id] = {
            "display_name": pr.display_name,
            "exit_code": pr.exit_code,
            "skipped": pr.skipped,
            "last_executed_at": pr.last_executed_at,
            "headline_metrics": pr.headline_metrics,
            "halt": pr.halt,
            "stdout": pr.stdout,
            "stderr": pr.stderr,
        }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated_at": generated_at,
        "phases": phases_out,
    }
    METRICS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    DASHBOARD_PATH.write_text(
        _build_dashboard(generated_at, results),
        encoding="utf-8",
    )

    worst = max((pr.exit_code for pr in results), default=0)
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
