"""Trust score components and dataclasses.

Three components are computed per facility, blended into a per-capability
raw score that the calibrator (agent.calibrate) maps to a calibrated
probability and prediction set.

Phase 4 update: `compute_iphs_alignment_component` now returns a
per-capability mapping (`dict[str, float]`) sourced from the
`CapabilityValidation` results emitted by the IPHS validator. Phase 3
treated this as a flat 1.0 placeholder; that path is preserved when
no validations are supplied so the Phase 3 eval still runs in isolation.

The frozen FacilityClaim schema is not extended; FacilityTrustScore is a
sibling artifact joined to FacilityClaim by source_record_id.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from agent.schemas.facility import Capability, FacilityClaim
from agent.validator import CapabilityValidation


PredictionLabel = Literal["claimed", "not_claimed"]
Badge = Literal["green", "yellow", "red"]


def compute_self_consistency_component(caps: Sequence[Capability]) -> float:
    if not caps:
        return 0.0
    return sum(cap.confidence_self_consistency for cap in caps) / len(caps)


def compute_source_completeness_component(claim: FacilityClaim) -> float:
    """Mean of five sub-signals, each in [0, 1]:
    - schema-derived `data_completeness_score`
    - presence of an official phone
    - presence of an official website
    - capped social-media presence count (≥5 saturates at 1.0)
    - recency: 1.0 if updated within 1y, 0.7 within 2y, 0.3 if older, 0.5 if unknown
    """
    completeness = claim.data_completeness_score or 0.0
    phone = 1.0 if claim.has_official_phone else 0.0
    website = 1.0 if claim.has_official_website else 0.0
    social = min(claim.social_media_presence_count, 5) / 5.0
    days = claim.days_since_last_update
    if days is None:
        recency = 0.5
    elif days < 365:
        recency = 1.0
    elif days < 730:
        recency = 0.7
    else:
        recency = 0.3
    return (completeness + phone + website + social + recency) / 5.0


def compute_iphs_alignment_component(
    claim: FacilityClaim,
    validations: Sequence[CapabilityValidation] | None = None,
) -> dict[str, float]:
    """Per-capability IPHS alignment scores keyed by capability name.

    Phase 3 used a placeholder facility-level scalar; Phase 4 returns
    per-capability scores from the validator. Capabilities without a
    validation (e.g., when `validations` is None or omits a name) default
    to 1.0 — the blender does not penalize the absence of validator
    coverage.
    """
    by_name: dict[str, float] = {}
    if validations:
        for validation in validations:
            by_name[validation.capability_name] = validation.iphs_alignment_score
    return {cap.name: by_name.get(cap.name, 1.0) for cap in claim.capabilities}


def summarize_iphs_alignment(per_cap: dict[str, float]) -> float:
    """Facility-level summary (mean) of per-capability iphs alignment scores."""
    if not per_cap:
        return 1.0
    return sum(per_cap.values()) / len(per_cap)


def raw_score_for_capability(
    cap: Capability,
    source_completeness: float,
    iphs_alignment: float,
) -> float:
    """Equal-weight blend of three components into [0, 1]."""
    return (cap.confidence_self_consistency + source_completeness + iphs_alignment) / 3.0


def badge_for_prediction(predicted_claimed: bool, prediction_set: list[PredictionLabel]) -> Badge:
    if len(prediction_set) >= 2:
        return "yellow"
    if not prediction_set:
        return "yellow"
    only = prediction_set[0]
    if only == "claimed" and predicted_claimed:
        return "green"
    if only == "not_claimed" and not predicted_claimed:
        return "green"
    return "red"


@dataclass(frozen=True)
class CapabilityScore:
    name: str
    claimed: bool
    confidence_self_consistency: float
    iphs_alignment: float
    violated_rule_ids: list[str]
    raw_score: float
    calibrated_score: float
    prediction_set: list[PredictionLabel]
    badge: Badge


@dataclass(frozen=True)
class FacilityTrustScore:
    source_record_id: str
    facility_name: str
    self_consistency_component: float
    source_completeness_component: float
    iphs_alignment_component: float
    blended_score: float
    capability_scores: list[CapabilityScore]
