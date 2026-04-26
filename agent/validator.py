"""Phase 4 IPHS validator agent.

Rule-based (not LLM-based) validator that emits one CapabilityValidation
per capability in the input FacilityClaim. Each validation carries the
per-capability iphs_alignment_score, the list of violated rule IDs, the
supporting evidence quotes, and a one-sentence reasoning string for the
citation UI.

Algorithm (per spec):
    score = 1.0
    for rule in rules:
        if not rule_applies(rule, claim): continue
        if cap.name not in trigger_set(rule): continue
        missing = [e for e in rule['required_evidence'] if e not in cap_names]
        if missing:
            score -= 0.25 * len(missing)
            violated_rules.append(rule['id'])
    score = max(0.0, score)

Capabilities that no rule triggers on retain alignment 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import yaml

from agent.schemas.facility import FacilityClaim

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "data" / "iphs_rules.yaml"

WILDCARD_APPLIES_TO = "any_facility_with_capability_X"
PER_MISSING_EVIDENCE_PENALTY = 0.25


@dataclass(frozen=True)
class CapabilityValidation:
    source_record_id: str
    capability_name: str
    iphs_alignment_score: float
    violated_rules: list[str]
    supporting_evidence: list[str]
    reasoning: str


@dataclass
class ValidatorAgent:
    rules: list[dict] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_RULES_PATH) -> "ValidatorAgent":
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or []
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a list of rules")
        return cls(rules=data)

    def _trigger_set(self, rule: dict) -> set[str]:
        trigger = rule.get("trigger_capability")
        if isinstance(trigger, str):
            return {trigger}
        if isinstance(trigger, list):
            return set(trigger)
        return set()

    def _applies(self, rule: dict, claim: FacilityClaim) -> bool:
        applies_to = rule.get("applies_to") or []
        if WILDCARD_APPLIES_TO in applies_to:
            return True
        if not applies_to:
            return False
        return claim.iphs_equivalent_tier in applies_to

    def validate_facility(
        self, claim: FacilityClaim, raw_text: str = ""
    ) -> list[CapabilityValidation]:
        # raw_text is accepted for forward compatibility (Phase 5+ may use it
        # for evidence-quote re-grounding); v1 relies on the canonical names
        # already present in the FacilityClaim.
        del raw_text  # unused in v1

        cap_names = {cap.name for cap in claim.capabilities}
        cap_evidence = {cap.name: cap.evidence_quote for cap in claim.capabilities}

        validations: list[CapabilityValidation] = []
        for cap in claim.capabilities:
            score = 1.0
            violated: list[str] = []
            evidence: list[str] = []
            for rule in self.rules:
                if cap.name not in self._trigger_set(rule):
                    continue
                if not self._applies(rule, claim):
                    continue
                required = list(rule.get("required_evidence") or [])
                missing = [name for name in required if name not in cap_names]
                if not required:
                    # Tier-scope rules (R20*) violate by tier alone.
                    score -= PER_MISSING_EVIDENCE_PENALTY
                    violated.append(rule["id"])
                    evidence.append(
                        f"{rule['id']}: tier={claim.iphs_equivalent_tier} violates {rule['flag_text']}"
                    )
                elif missing:
                    score -= PER_MISSING_EVIDENCE_PENALTY * len(missing)
                    violated.append(rule["id"])
                    evidence.append(
                        f"{rule['id']}: trigger evidence_quote={cap_evidence.get(cap.name, '')!r}; "
                        f"missing required evidence={missing}"
                    )
            score = max(0.0, score)
            reasoning = self._reason(cap.name, violated, score)
            validations.append(
                CapabilityValidation(
                    source_record_id=claim.source_record_id,
                    capability_name=cap.name,
                    iphs_alignment_score=score,
                    violated_rules=violated,
                    supporting_evidence=evidence,
                    reasoning=reasoning,
                )
            )
        return validations

    @staticmethod
    def _reason(cap_name: str, violated: Sequence[str], score: float) -> str:
        if not violated:
            return f"Capability '{cap_name}' triggered no IPHS rule; alignment 1.00."
        rule_list = ", ".join(violated)
        return (
            f"Capability '{cap_name}' triggered rule(s) {rule_list}; "
            f"alignment {score:.2f}."
        )
