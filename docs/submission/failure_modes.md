# Failure modes and scope limits

This one-pager states **what the system does not do** and **how to interpret outputs**. It is part of the submission packet for judges and partners.

## 1. IPHS is a benchmark-equivalent comparison, not strict compliance

Roughly **99%** of rows in the Virtue-style facility corpus are **private** providers **outside** the formal IPHS public-facility hierarchy. The validator therefore uses an **`any_facility_with_capability_X`** style of rule application (see `data/iphs_rules.yaml` header): IPHS clauses are used as a **structured, citable benchmark** for “what evidence should exist if this claim were true,” **not** as a determination that a private clinic is “IPHS compliant” or legally certified.

## 2. Calibration is conservative at the current gold scale

The conformal and isotonic layer is fit on a **30-record** human gold slice. At that scale, **prediction sets are wide** and **most capability badges read yellow** in the demo—by design of small-sample conformal methods, not because every facility is uniformly low quality. When **Phase 6** ingests the **full ~10K** extraction and the calibration pool scales to on the order of **~1500** labeled capability rows (proportional split), **intervals tighten** and the **green** rate should **increase** for genuinely well-evidenced claims **without** changing the rulebook.

## 3. No medical diagnosis; no replacement for clinical judgment

The pipeline **does not diagnose** patients, **does not prescribe** treatment, and **does not** replace physicians, nurses, or ASHAs. It is a **triage and audit** aid: structured **facility-level claims** vs **normative evidence** expectations, with **human-in-the-loop** for any referral, surgical booking, or policy decision.

## 4. No real-time data freshness

The **10K** dataset and JSONL artifacts in the prototype are a **snapshot**, not a live national feed. Staleness, closures, staffing churn, and unreported equipment changes are **not** continuously reconciled. Any operational deployment would need explicit **refresh cadence**, **source versioning**, and **override** workflows.

## 5. Economic and stack disclaimers (brief)

**Frontier** chat models were used to build the **30-record reference** extraction slice; **production** batching for the full corpus is planned on **open-weight** **Qwen 2.5 7B** via **vLLM** on **Colab Pro** to avoid **per-token frontier API** costs at 10K scale. Residual costs (GPU rental, hosting, human QA) still apply and must be budgeted for NGO or government pilots.

## 6. Validator coverage is a subset of IPHS 2022

The shipped rulebook implements **17** machine-checkable rules distilled from **IPHS 2022** across volumes I–IV (plus SARA-style phrasing where noted). **Many** clinical and administrative requirements are **not** encoded; absence of a flag does **not** prove adequacy.

---

**Bottom line:** Treat outputs as **audit hints** with **citations**, not as accreditation. Combine with **site visits**, **program data**, and **clinical** oversight before any high-stakes action.
