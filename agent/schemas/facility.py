# DO NOT MODIFY without explicit approval. Frozen at Phase 1.
from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, field_validator


FacilityCategory = Literal[
    "hospital",
    "clinic",
    "dental",
    "pharmacy",
    "diagnostic",
    "single_practitioner",
    "other",
]

IphsEquivalentTier = Literal[
    "shc_hwc",
    "phc",
    "chc_non_fru",
    "chc_fru",
    "sdh_dh",
]


def build_source_record_id(
    name: str,
    zip_or_postcode: str | None,
    latitude: float | str | None,
    longitude: float | str | None,
) -> str:
    """Build sha256(name|zip|lat|lon)[:16] for deterministic source joins."""
    key = "|".join(
        [
            str(name or "").strip(),
            str(zip_or_postcode or "").strip(),
            str(latitude or "").strip(),
            str(longitude or "").strip(),
        ]
    )
    return sha256(key.encode("utf-8")).hexdigest()[:16]


class Capability(BaseModel):
    name: str = Field(..., min_length=1)
    claimed: bool
    evidence_quote: str = Field(..., min_length=1)
    evidence_char_offset: tuple[int, int]
    confidence_self_consistency: float = Field(..., ge=0.0, le=1.0)
    iphs_equivalent_tier: IphsEquivalentTier | None = None
    iphs_rule_violations: list[str] = Field(default_factory=list)

    @field_validator("evidence_char_offset")
    @classmethod
    def validate_offsets(cls, value: tuple[int, int]) -> tuple[int, int]:
        start, end = value
        if start < 0 or end <= start:
            raise ValueError("evidence_char_offset must be a valid [start, end) span")
        return value


class FacilityClaim(BaseModel):
    source_record_id: str = Field(
        ...,
        min_length=16,
        max_length=16,
        description="Deterministic sha256(name|zip|lat|lon)[:16] source key.",
    )
    facility_name: str = Field(..., min_length=1)
    facility_category: FacilityCategory
    iphs_equivalent_tier: IphsEquivalentTier | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    data_completeness_score: float | None = None
    has_official_phone: bool
    has_official_website: bool
    social_media_presence_count: int
    days_since_last_update: int | None = None
    declared_doctor_count: int | None = None
    declared_capacity: int | None = None

    @field_validator("capabilities")
    @classmethod
    def require_unique_capability_names(
        cls, value: list[Capability]
    ) -> list[Capability]:
        names = [capability.name.lower().strip() for capability in value]
        if len(names) != len(set(names)):
            raise ValueError("capability names must be unique per facility")
        return value
