# Tech video script — 60 seconds (shot list)

---

## 0:00–0:10 — Architecture (diagram)

- **Shot:** Static slide or screen: single flowchart (export from [`architecture_diagram.mermaid`](architecture_diagram.mermaid)) — VF / bronze facility text → **Phase 2 extraction** → **Phase 3 calibration** → **Phase 4 IPHS validator** → **FastAPI `/trace/{id}`** → **React (Lovable)** + **MLflow** observability.
- **VO one-liner:** *Structured claims, statistical calibration, rule citations—same contract for NGO dashboards and ASHA-facing tools.*

---

## 0:10–0:30 — Calibration story (20s core; extend slightly if pacing allows)

- **Shot:** Notebook or terminal excerpt: `phase3_calibration.py` / `agent/calibrate.py` — **IsotonicRegression** + **MAPIE `SplitConformalClassifier`**, **α = 0.10** → nominal **90%** coverage target on per-capability claim verification.
- **VO — numbers (memorize):** On the **30-record** gold set, **empirical coverage was 0.9286** ( **92.86%** ) against the **0.90** nominal target—slightly **above** target because the pipeline is still **conservative** at small **n**.
- **Shot:** Table or overlay: **validator** produces per-capability **`iphs_alignment` ∈ {0.00, 0.50, 1.00}** from rule deduction (partial evidence vs full alignment).
- **VO:** The **isotonic** blender on raw trust components, wrapped in **split conformal prediction**, is what yields **finite-sample** **90%**-style guarantees on **per-capability** claim verification—not hand-waved model confidence.
- **Forward-looking line:** When the **full 10K** extraction lands in **Phase 6**, the calibration split scales to on the order of **~1500** capability rows for refit—**intervals tighten** and badge **green** rate should **rise** as conformal sets shrink with data.

---

## 0:30–0:50 — Validator agent (per-capability rules)

- **Shot:** `phase4_validations.jsonl` or UI cards: **`c616c9769f2afbd7`** with **R01 / R02** on surgery-related capabilities; quick cut to **R33** (emergency vs ambulance evidence) or **R09** (obstetric equipment) on another `source_record_id`.
- **VO:** **17 YAML rules** from **IPHS 2022** across volumes; **`rules_index`** in the trace response feeds the citation UI without a second round-trip.

---

## 0:50–1:00 — Honest failure modes

- **Shot:** Title card: **“What this does NOT do.”**
- **VO (bullets, ~2s each):** No **diagnosis**; **not** a replacement for **clinical judgment**; **IPHS** is a **public-sector benchmark**, not a private-clinic compliance certificate; **no live data**—10K is a **snapshot**; calibration is **conservative** at **n = 30** until Phase 6 scale-up.
- **End frame:** Link or QR to **`failure_modes.md`** in repo / submission packet.

---

## Extraction backbone (10s mention if architecture block runs long)

- If architecture block is only 8s, add here: **Production extraction** for the full corpus is **Qwen 2.5 7B Instruct** on **vLLM** (**Colab Pro**); **Sonnet 4.6** defines the **30-record frontier reference** slice only—**economic feasibility** for NGOs / departments.
