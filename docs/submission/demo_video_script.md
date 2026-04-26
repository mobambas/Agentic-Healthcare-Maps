# Demo video script — 60 seconds (shot list)

**Positioning (voiceover or lower-third once):** Deployable pipeline on **open-weight Qwen 2.5 7B (vLLM, Colab Pro)** for the **10K** audit—**frontier Sonnet 4.6** only on the **30-record reference** slice for comparison, not the production cost path.

---

## 0:00–0:05 — Cold open (lead with hero record)

- **Shot:** Full-screen UI already on **`source_record_id c616c9769f2afbd7`** — **Dr. Pratik Dhabalia Joint Replacement**; facility name + ID visible; no VO yet (or one line: *“Same hospital—six different answers.”*).

---

## 0:05–0:12 — Hook (Hindi, on-camera or captioned)

- **Shot:** ASHA worker (or actor in uniform), direct to camera, rural clinic or map B-roll.
- **Line (Hindi):** *"नज़दीकी अस्पताल में जॉइंट रिप्लेसमेंट सर्जरी होती है—क्या वहाँ एनेस्थीसिया डॉक्टर और ऑपरेशन थिएटर दोनों हैं?"* (Subtitles in English: joint replacement is advertised—are an anaesthetist and a working OT actually there?)
- **Audio:** Quiet room tone; optional soft tabla/ambient under 20%.

---

## 0:12–0:22 — Problem framing (body-count / rupee-cost anchor)

- **Shot:** Split: brief quote on-screen (“**70%** rural”, “discovery and coordination crisis”) from Challenge 03 motivation; cut to family travel stock or static map.
- **VO:** Wrong facility choice wastes **time and money** when directories are **unstructured** and **unverified**—exactly the “truth gap” the brief names.
- **Lower-third:** *Trust, not trust-me marketing.*

---

## 0:22–0:52 — Golden path (hero record + trace visible)

- **Shot:** Screen record: React / Lovable UI (or Streamlit citation preview) **landing directly** on **`source_record_id = c616c9769f2afbd7`** — **Dr. Pratik Dhabalia Joint Replacement**.
- **Narration beat 1 — within-record discrimination:** On **one** facility row, **three** surgical capability claims show **`iphs_alignment = 0.00`** with **R01** (anaesthesia) and **R02** (functional OT) violations; **three sibling capabilities** at the **same** facility show **`iphs_alignment = 1.00`** with **no** violations (fracture clinic, family medicine, sports orthopedics). State clearly: *capability-level* signal, not a lazy facility-wide label.
- **Shot:** Second pane or PiP: **MLflow trace** or network panel showing **`GET /trace/c616c9769f2afbd7`** — spans or JSON highlighting **evidence_quote**, **violated_rules**, **rules_index** citation strings (IPHS 2022 Vol II).
- **Optional flash:** Blended trust line from preview: **blended ≈ 0.73**, **six** yellow capability badges (no green) — “conservative at 30-record calibration scale.”

---

## 0:52–1:00 — Close (sponsor stack)

- **Shot:** Logo lockup or fast montage: **Databricks** (data + MLflow traces), **Google Colab Pro + vLLM + Qwen 2.5 7B** (open-weight extraction backbone), **Vercel** (FastAPI proxy), **Lovable** (React client). Optional: **OpenAI** if hub credits used for Codex side workflows.
- **Line:** *Calibrated claims, cited rules, commodity GPUs—built for the partners who cannot pay frontier-token rent on ten thousand rows.*

---

## Production notes

- Pre-record backup by **hour 18** (playbook); warm Model Serving / API if any cloud steps remain in the live path.
- If Hindi on-camera is not available, use **Remotion + Edge TTS** or a fluent speaker clip; keep **Hindi audio + English subs** for judges.
