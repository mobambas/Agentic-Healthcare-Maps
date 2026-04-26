"""Split conformal calibration over per-capability confidence.

Pipeline:
    1. For every (record, capability) in phase2_extractions.jsonl, compute the
       three trust-score components and a raw_score = mean of the three.
    2. Label y=1 if the capability's canonicalized name appears in the
       canonicalized gold capability set for that record, else y=0.
    3. Split records (not capabilities) into 20 calibration / 10 held-out
       using a deterministic seed.
    4. Fit IsotonicBinaryClassifier on the 20 calibration records' caps to
       map raw_score -> P(correct).
    5. Wrap the prefit classifier in mapie's SplitConformalClassifier with
       confidence_level=0.90 (alpha=0.10) and conformity_score='lac'.
    6. Conformalize on the same 20 calibration records' caps. (Note: with
       only 30 records we share the fit and conformalize sets; the textbook
       split-conformal coverage guarantee is therefore slightly optimistic.
       We measure empirical coverage on the 10-record held-out split as
       the honest validation signal.)
    7. Return the calibrated scorer and a coverage report.

Public API:
    build_capability_dataset(extractions, gold, synonym_to_canonical)
    fit_calibrator(extractions, gold, synonym_to_canonical, *, seed=42,
                   alpha=0.10, n_cal_records=20)
        -> (CalibratedTrustScorer, CoverageReport)
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from mapie.classification import SplitConformalClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.isotonic import IsotonicRegression

from agent.schemas.facility import FacilityClaim
from agent.trust_score import (
    PredictionLabel,
    compute_iphs_alignment_component,
    compute_source_completeness_component,
    raw_score_for_capability,
)
from agent.validator import CapabilityValidation

ROOT = Path(__file__).resolve().parents[1]
ALIASES_PATH = ROOT / "data" / "capability_aliases.yaml"

DEFAULT_ALPHA = 0.10
DEFAULT_N_CAL_RECORDS = 20


def load_synonym_to_canonical(path: Path = ALIASES_PATH) -> dict[str, str]:
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


def canonicalize(name: str, synonym_to_canonical: dict[str, str]) -> str:
    return synonym_to_canonical.get(name, name)


class IsotonicBinaryClassifier(BaseEstimator, ClassifierMixin):
    """Wraps sklearn IsotonicRegression as a binary classifier exposing predict_proba.

    Required so mapie's SplitConformalClassifier can compute LAC nonconformity scores.
    """

    def fit(self, X, y) -> "IsotonicBinaryClassifier":
        x_flat = np.asarray(X).ravel().astype(float)
        y_arr = np.asarray(y).astype(int)
        self._iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._iso.fit(x_flat, y_arr)
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = 1
        return self

    def predict_proba(self, X) -> np.ndarray:
        x_flat = np.asarray(X).ravel().astype(float)
        p1 = np.clip(self._iso.predict(x_flat), 1e-3, 1 - 1e-3)
        p0 = 1 - p1
        return np.column_stack([p0, p1])

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] > 0.5).astype(int)


@dataclass
class CapabilityRow:
    source_record_id: str
    name: str
    raw_score: float
    label: int
    self_consistency: float
    source_completeness: float
    iphs_alignment: float


@dataclass
class CalibratedTrustScorer:
    classifier: IsotonicBinaryClassifier
    scc: SplitConformalClassifier
    confidence_level: float
    alpha: float

    def predict_set_batch(
        self, raw_scores: Sequence[float]
    ) -> tuple[list[list[PredictionLabel]], list[float]]:
        if not raw_scores:
            return [], []
        x = np.asarray(raw_scores, dtype=float).reshape(-1, 1)
        _, set_mask = self.scc.predict_set(x)
        if set_mask.ndim == 3:
            # Some mapie configurations return (n_samples, n_classes, n_alphas)
            set_mask = set_mask[:, :, 0]
        proba = self.classifier.predict_proba(x)[:, 1]

        sets: list[list[PredictionLabel]] = []
        for row in set_mask:
            entry: list[PredictionLabel] = []
            if bool(row[1]):
                entry.append("claimed")
            if bool(row[0]):
                entry.append("not_claimed")
            sets.append(entry)
        return sets, proba.tolist()


@dataclass
class CoverageReport:
    n_cal_records: int
    n_cal_caps: int
    n_test_records: int
    n_test_caps: int
    alpha: float
    confidence_level: float
    empirical_coverage: float
    cal_label_balance: tuple[int, int]
    test_label_balance: tuple[int, int]


def build_capability_dataset(
    extractions: dict[str, dict],
    gold: dict[str, dict],
    synonym_to_canonical: dict[str, str],
    validations_by_sid: dict[str, list[CapabilityValidation]] | None = None,
) -> list[CapabilityRow]:
    rows: list[CapabilityRow] = []
    for sid, extraction in extractions.items():
        if sid not in gold:
            continue
        claim = FacilityClaim.model_validate(extraction["claim"])
        gold_names = {
            canonicalize(cap["name"], synonym_to_canonical)
            for cap in gold[sid]["capabilities"]
        }
        completeness = compute_source_completeness_component(claim)
        validations = (validations_by_sid or {}).get(sid)
        iphs_by_cap = compute_iphs_alignment_component(claim, validations)
        for cap in claim.capabilities:
            canonical_name = canonicalize(cap.name, synonym_to_canonical)
            iphs_cap = iphs_by_cap.get(cap.name, 1.0)
            raw = raw_score_for_capability(cap, completeness, iphs_cap)
            rows.append(
                CapabilityRow(
                    source_record_id=sid,
                    name=canonical_name,
                    raw_score=raw,
                    label=1 if canonical_name in gold_names else 0,
                    self_consistency=cap.confidence_self_consistency,
                    source_completeness=completeness,
                    iphs_alignment=iphs_cap,
                )
            )
    return rows


def split_records(
    extraction_sids: Sequence[str],
    gold_sids: Sequence[str],
    seed: int,
    n_cal_records: int,
) -> tuple[set[str], set[str]]:
    sids = sorted(set(extraction_sids) & set(gold_sids))
    rng = random.Random(seed)
    rng.shuffle(sids)
    cal = set(sids[:n_cal_records])
    test = set(sids[n_cal_records:])
    return cal, test


def fit_calibrator(
    extractions: dict[str, dict],
    gold: dict[str, dict],
    synonym_to_canonical: dict[str, str],
    validations_by_sid: dict[str, list[CapabilityValidation]] | None = None,
    *,
    seed: int = 42,
    alpha: float = DEFAULT_ALPHA,
    n_cal_records: int = DEFAULT_N_CAL_RECORDS,
) -> tuple[CalibratedTrustScorer, CoverageReport]:
    cal_sids, test_sids = split_records(
        list(extractions.keys()), list(gold.keys()), seed=seed, n_cal_records=n_cal_records
    )

    rows = build_capability_dataset(
        extractions, gold, synonym_to_canonical, validations_by_sid=validations_by_sid
    )
    cal_rows = [row for row in rows if row.source_record_id in cal_sids]
    test_rows = [row for row in rows if row.source_record_id in test_sids]

    if len(cal_rows) < 5:
        raise ValueError(
            f"Only {len(cal_rows)} calibration capabilities; need at least 5 to fit isotonic."
        )
    if len({row.label for row in cal_rows}) < 2:
        raise ValueError(
            "Calibration set has only one label class; cannot fit a binary calibrator. "
            "Either gold has 100% true positives in this split (suspicious) or 0% (more "
            "suspicious). Inspect the gold-vs-extraction overlap before proceeding."
        )

    x_cal = np.array([row.raw_score for row in cal_rows]).reshape(-1, 1)
    y_cal = np.array([row.label for row in cal_rows])

    classifier = IsotonicBinaryClassifier().fit(x_cal, y_cal)
    confidence_level = 1.0 - alpha
    scc = SplitConformalClassifier(
        estimator=classifier,
        confidence_level=confidence_level,
        conformity_score="lac",
        prefit=True,
        random_state=seed,
    )
    scc.conformalize(x_cal, y_cal)

    scorer = CalibratedTrustScorer(
        classifier=classifier,
        scc=scc,
        confidence_level=confidence_level,
        alpha=alpha,
    )

    if test_rows:
        x_test = np.array([row.raw_score for row in test_rows]).reshape(-1, 1)
        _, set_mask = scc.predict_set(x_test)
        if set_mask.ndim == 3:
            set_mask = set_mask[:, :, 0]
        labels = np.array([row.label for row in test_rows])
        # Class 0 is at column 0, class 1 is at column 1; coverage = true label included.
        covered = set_mask[np.arange(len(labels)), labels]
        empirical_coverage = float(covered.mean())
    else:
        empirical_coverage = float("nan")

    report = CoverageReport(
        n_cal_records=len(cal_sids),
        n_cal_caps=len(cal_rows),
        n_test_records=len(test_sids),
        n_test_caps=len(test_rows),
        alpha=alpha,
        confidence_level=confidence_level,
        empirical_coverage=empirical_coverage,
        cal_label_balance=(
            int(np.sum(y_cal == 0)),
            int(np.sum(y_cal == 1)),
        ),
        test_label_balance=(
            int(sum(1 for row in test_rows if row.label == 0)),
            int(sum(1 for row in test_rows if row.label == 1)),
        ),
    )
    return scorer, report
