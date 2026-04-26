"""FastAPI route serving combined extraction + validation + trace data.

GET /trace/{source_record_id} returns a single JSON document containing:
    - facility_claim: the FacilityClaim from data/phase2_extractions.jsonl
    - trust_score: the FacilityTrustScore record from data/phase3_trust_scores.jsonl,
      with per-capability iphs_alignment, violated_rule_ids, prediction_set, badge
    - validations: full CapabilityValidation list from data/phase4_validations.jsonl
      (reasoning + supporting_evidence per capability)
    - rules_index: lightweight {rule_id -> {flag_text, citation, severity}} lookup
      so the React UI can render rule citations on hover without a second call
    - traces: list of MLflow trace summaries matching this source_record_id
      with the span hierarchy as a tree

This is the canonical surface the React citation UI consumes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import mlflow
import yaml
from fastapi import APIRouter, HTTPException
from mlflow.tracking import MlflowClient

ROOT = Path(__file__).resolve().parents[2]
EXTRACT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
TRUST_PATH = ROOT / "data" / "phase3_trust_scores.jsonl"
VALIDATIONS_PATH = ROOT / "data" / "phase4_validations.jsonl"
RULES_PATH = ROOT / "data" / "iphs_rules.yaml"
DEFAULT_TRACKING_URI = f"sqlite:///{ROOT}/.mlflow/mlflow.db"
DEFAULT_EXPERIMENT = "agentic-healthcare-maps"

router = APIRouter()


def _load_jsonl_index(path: Path, key: str = "source_record_id") -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out[record[key]] = record
    return out


def _load_rules_index() -> dict[str, dict]:
    if not RULES_PATH.exists():
        return {}
    with RULES_PATH.open(encoding="utf-8") as fh:
        rules = yaml.safe_load(fh) or []
    return {
        rule["id"]: {
            "flag_text": rule.get("flag_text", ""),
            "citation": rule.get("citation", ""),
            "severity": rule.get("severity", ""),
            "framework": rule.get("framework", ""),
        }
        for rule in rules
    }


def _spans_to_tree(spans: list[Any]) -> list[dict]:
    nodes_by_id: dict[str, dict] = {}
    for span in spans:
        node = {
            "span_id": span.span_id,
            "name": span.name,
            "span_type": span.span_type,
            "start_time_ns": span.start_time_ns,
            "end_time_ns": span.end_time_ns,
            "duration_ms": (span.end_time_ns - span.start_time_ns) / 1_000_000
            if span.end_time_ns
            else None,
            "attributes": dict(span.attributes or {}),
            "children": [],
        }
        nodes_by_id[span.span_id] = node
    roots: list[dict] = []
    for span in spans:
        node = nodes_by_id[span.span_id]
        parent_id = getattr(span, "parent_id", None)
        if parent_id and parent_id in nodes_by_id:
            nodes_by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def _fetch_traces_for(source_record_id: str) -> list[dict]:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    experiment_name = os.getenv("MLFLOW_EXPERIMENT", DEFAULT_EXPERIMENT)
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        return []
    try:
        traces = mlflow.search_traces(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tag.source_record_id = '{source_record_id}'",
            return_type="list",
        )
    except Exception:
        return []
    payloads: list[dict] = []
    for trace in traces or []:
        info = trace.info
        try:
            spans = trace.data.spans
        except Exception:
            spans = []
        payloads.append(
            {
                "trace_id": info.trace_id,
                "experiment_id": info.experiment_id,
                "request_time_ms": info.request_time,
                "status": info.state,
                "tags": dict(info.tags or {}),
                "execution_time_ms": info.execution_duration,
                "span_tree": _spans_to_tree(spans),
            }
        )
    return payloads


@router.get("/trace/{source_record_id}")
def get_trace(source_record_id: str) -> dict:
    extractions = _load_jsonl_index(EXTRACT_PATH)
    if source_record_id not in extractions:
        raise HTTPException(
            status_code=404,
            detail=f"source_record_id {source_record_id!r} not in {EXTRACT_PATH.name}",
        )
    trust = _load_jsonl_index(TRUST_PATH)
    validations = _load_jsonl_index(VALIDATIONS_PATH)
    rules_index = _load_rules_index()
    extr_record = extractions[source_record_id]
    return {
        "source_record_id": source_record_id,
        "facility_claim": extr_record["claim"],
        "extraction_meta": {
            "rejection_count": extr_record.get("rejection_count"),
            "n_samples_succeeded": extr_record.get("n_samples_succeeded"),
            "n_samples_target": extr_record.get("n_samples_target"),
            "model": extr_record.get("model"),
        },
        "trust_score": trust.get(source_record_id),
        "validations": (validations.get(source_record_id) or {}).get("validations", []),
        "rules_index": rules_index,
        "traces": _fetch_traces_for(source_record_id),
    }
