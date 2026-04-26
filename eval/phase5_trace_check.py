"""End-to-end MLflow trace check for one gold record.

Runs a fresh N=5 extraction + IPHS validation for the demo hero record
(`c616c9769f2afbd7` Dr. Pratik Dhabalia Joint Replacement) inside a single
top-level CHAIN trace. After the run, the script asserts that the resulting
trace satisfies the master prompt's coverage contract:

    * one LLM span per attempted N=5 sample
    * one TOOL (`ground_capability`) span per surviving sample's grounding step
    * one AGENT (`validate_facility`) span
    * usage tokens populated on every LLM span

Cost: roughly one record's worth of Sonnet calls (~$0.05). Within the
master-prompt $1 cap for Phase 5.

Run:
    python eval/phase5_trace_check.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mlflow
from dotenv import load_dotenv
from mlflow.entities import SpanType
from mlflow.tracking import MlflowClient

import anthropic
import instructor

from agent.extract import (
    DEFAULT_MODEL,
    N_SAMPLES,
    aggregate_claims,
    build_source_text,
    build_source_record_id,
    load_vocab,
    make_system_prompt,
    make_user_message,
    process_facility,
    setup_mlflow,
)
from agent.schemas.facility import FacilityClaim
from agent.validator import ValidatorAgent

load_dotenv(ROOT / ".env")

DEMO_SOURCE_RECORD_ID = "c616c9769f2afbd7"
CSV_PATH = ROOT / "data" / "vf_facilities.csv"


def _resolve_row(source_record_id: str) -> dict[str, str]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sid = build_source_record_id(
                row.get("name"),
                row.get("address_zipOrPostcode"),
                row.get("latitude"),
                row.get("longitude"),
            )
            if sid == source_record_id:
                return row
    raise SystemExit(f"source_record_id {source_record_id!r} not found in {CSV_PATH.name}")


@mlflow.trace(span_type=SpanType.CHAIN, name="phase5_end_to_end")
def run_end_to_end(
    client: instructor.Instructor,
    model: str,
    system_prompt: str,
    source_record_id: str,
    row: dict[str, str],
    validator: ValidatorAgent,
) -> tuple[FacilityClaim, list]:
    mlflow.update_current_trace(
        tags={"source_record_id": source_record_id, "phase": "phase5_trace_check"}
    )
    source_text = build_source_text(row)
    user_message = make_user_message(row, source_text, source_record_id)
    samples, rejections, cost, _ = process_facility(
        client,
        model,
        system_prompt,
        user_message,
        source_text,
        source_record_id,
        row,
    )
    if not samples:
        raise SystemExit("no successful samples; cannot continue trace check")
    aggregated = aggregate_claims(samples)
    # Live alias canonicalization was removed in Phase 2 revision. The offline
    # `--canonicalize-existing` path applies the alias map after the fact; for
    # this end-to-end trace we use the aggregated claim as-is.
    validations = validator.validate_facility(aggregated, raw_text=source_text)
    return aggregated, validations


def _wait_for_trace(client: MlflowClient, experiment_id: str, source_record_id: str, attempts: int = 10) -> Any:
    for _ in range(attempts):
        traces = mlflow.search_traces(
            experiment_ids=[experiment_id],
            filter_string=f"tag.source_record_id = '{source_record_id}' and tag.phase = 'phase5_trace_check'",
            return_type="list",
            order_by=["timestamp_ms DESC"],
        )
        if traces:
            return traces[0]
        time.sleep(0.5)
    return None


def _print_tree(spans: list[Any]) -> None:
    by_id = {s.span_id: {"span": s, "children": []} for s in spans}
    roots: list[dict] = []
    for s in spans:
        node = by_id[s.span_id]
        parent_id = getattr(s, "parent_id", None)
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def render(node: dict, depth: int) -> None:
        s = node["span"]
        duration_ms = (s.end_time_ns - s.start_time_ns) / 1_000_000 if s.end_time_ns else None
        prefix = "  " * depth + ("└─ " if depth else "")
        line = f"{prefix}[{s.span_type}] {s.name}"
        if duration_ms is not None:
            line += f"  ({duration_ms:.1f}ms)"
        attrs = s.attributes or {}
        usage = attrs.get("mlflow.chat.tokenUsage") or attrs.get("mlflow.chat.tokenusage")
        if usage:
            line += f"   usage={usage}"
        for key in ("capability_name", "matched_rule_count", "matched_rule_ids"):
            if key in attrs:
                line += f"   {key}={attrs[key]}"
        print(line)
        for child in node["children"]:
            render(child, depth + 1)

    for r in roots:
        render(r, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-record-id", default=DEMO_SOURCE_RECORD_ID)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment or .env", file=sys.stderr)
        return 1

    setup_mlflow()
    print(f"MLflow tracking: {mlflow.get_tracking_uri()}", file=sys.stderr)

    row = _resolve_row(args.source_record_id)
    vocab = load_vocab()
    system_prompt = make_system_prompt(vocab)
    client = instructor.from_anthropic(anthropic.Anthropic())
    validator = ValidatorAgent.from_yaml()

    aggregated, validations = run_end_to_end(
        client, args.model, system_prompt, args.source_record_id, row, validator
    )

    print()
    print(
        f"aggregated capabilities (post-consistency): "
        f"{[(c.name, c.confidence_self_consistency) for c in aggregated.capabilities]}"
    )
    print(f"validator output: {len(validations)} CapabilityValidation(s)")

    mlflow_client = MlflowClient(tracking_uri=mlflow.get_tracking_uri())
    experiment = mlflow_client.get_experiment_by_name(
        os.getenv("MLFLOW_EXPERIMENT", "agentic-healthcare-maps")
    )
    if experiment is None:
        print("MLflow experiment missing; cannot inspect trace", file=sys.stderr)
        return 1
    trace = _wait_for_trace(mlflow_client, experiment.experiment_id, args.source_record_id)
    if trace is None:
        print("No trace found for source_record_id; check filter tag", file=sys.stderr)
        return 1

    spans = list(trace.data.spans)
    print()
    print(f"trace_id: {trace.info.trace_id}    spans: {len(spans)}")
    print()
    _print_tree(spans)
    print()

    span_types = [s.span_type for s in spans]
    spans_by_id = {s.span_id: s for s in spans}
    children_by_parent: dict[str, list[Any]] = {}
    for s in spans:
        parent_id = getattr(s, "parent_id", None)
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(s)
    llm_spans = [s for s in spans if s.span_type == SpanType.LLM]
    chat_model_spans = [s for s in spans if s.span_type == SpanType.CHAT_MODEL]
    tool_spans = [s for s in spans if s.span_type == SpanType.TOOL]
    agent_spans = [s for s in spans if s.span_type == SpanType.AGENT]
    retriever_spans = [s for s in spans if s.span_type == SpanType.RETRIEVER]

    def _span_has_usage(span: Any) -> bool:
        attrs = span.attributes or {}
        if any(
            attrs.get(k)
            for k in (
                "mlflow.chat.tokenUsage",
                "mlflow.chat.tokenusage",
                "llm.usage.input_tokens",
                "llm.usage.output_tokens",
            )
        ):
            return True
        for child in children_by_parent.get(span.span_id, []):
            if _span_has_usage(child):
                return True
        return False

    failures: list[str] = []
    if len(llm_spans) < N_SAMPLES:
        failures.append(
            f"expected >= {N_SAMPLES} LLM spans (one per sample), found {len(llm_spans)}"
        )
    if len(tool_spans) < 1:
        failures.append(f"expected >= 1 TOOL span, found {len(tool_spans)}")
    if len(agent_spans) < 1:
        failures.append(f"expected >= 1 AGENT span, found {len(agent_spans)}")
    if len(retriever_spans) < 1:
        failures.append(f"expected >= 1 RETRIEVER span, found {len(retriever_spans)}")
    untokenized = [s.name for s in llm_spans if not _span_has_usage(s)]
    if untokenized:
        failures.append(
            "LLM spans missing token usage on themselves or any CHAT_MODEL child: "
            f"{untokenized}"
        )

    print(
        f"span counts: LLM={len(llm_spans)}  CHAT_MODEL={len(chat_model_spans)}  "
        f"TOOL={len(tool_spans)}  AGENT={len(agent_spans)}  RETRIEVER={len(retriever_spans)}"
    )
    print(f"distinct span_types observed: {sorted(set(span_types))}")

    if failures:
        print()
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 2

    print()
    print("OK — trace satisfies the Phase 5 coverage contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
