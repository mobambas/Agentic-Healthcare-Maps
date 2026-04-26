# Tech recording steps — 60s

Step-by-step capture instructions for the **tech video** (engineering rigor angle). Pair with the voiceover in `tech_video_script.md`.

**Hero record (continuity with demo):** `c616c9769f2afbd7` — Dr. Pratik Dhabalia Joint Replacement.
**Total target wall clock:** 60 seconds at normal speaking pace.

## Pre-recording (do once, before you hit record)

1. Open the project in your editor with these files visible in tabs (in order, left to right):
   1. `agent/schemas/facility.py` — frozen Pydantic schema
   2. `agent/extract.py` — extraction loop, around line 460 (`process_facility` decorator visible)
   3. `data/iphs_rules.yaml` — open at `R01` and `R02`
   4. `eval/phase3_calibration.py` — opens with the `fit_calibrator` import
2. In a terminal in the project root, pre-cat the trace dump so it scrolls cleanly:
   ```bash
   source .venv/bin/activate
   less data/phase5_trace_dump.txt
   ```
3. Open `artifacts/eval/dashboard.html` in a browser tab; scroll once to verify Phase 3's `empirical coverage = 0.9286` row is rendered.
4. Open `data/iphs_rules.yaml` in your editor at the R01/R02 stanza so the citations are visible without scrolling.
5. Use a clean OS theme. Close unrelated tabs. Mute notifications.

## Recording sequence (in order)

| t (s) | Action | What's on screen |
|---|---|---|
| 0–6   | **Open on the schema**: cursor on `agent/schemas/facility.py`, `Capability` class visible. Highlight `evidence_quote: str` and `evidence_char_offset: tuple[int, int]`. | The frozen contract. Every claim carries verbatim evidence + char offsets. |
| 6–14  | Switch tab to `agent/extract.py` `process_facility` function (look for `@mlflow.trace(span_type=SpanType.CHAIN, name="process_facility")`). Highlight the `for _ in range(n_samples):` loop and the `call_model(...)` line. | N=5 self-consistency, ranked-fuzz evidence grounding, mlflow CHAIN-LLM-TOOL spans. |
| 14–22 | Switch tab to `eval/phase3_calibration.py`. Show the `fit_calibrator(extractions, gold, synonym_to_canonical, validations_by_sid=...)` call. | Where MAPIE split conformal lives. Keep cursor near the line for emphasis. |
| 22–30 | Cut to the dashboard browser tab. Scroll to the **Phase 3** section. Show `empirical coverage = 0.9286   (target = 0.90, floor = 0.85)`. Pause 2 s. | The conformal-coverage hero number. |
| 30–40 | Switch to `data/iphs_rules.yaml` open at R01/R02. Show the structured fields: `id`, `severity: high`, `framework: IPHS Vol II — FRU CHC essential specialists`, `trigger_capability: [surgery_services, ...]`, `required_evidence: [anaesthesiology]`, `citation: IPHS 2022 Vol II — FRU CHC essential specialists list...`. | Citable, machine-checkable rules. |
| 40–52 | Cut to the terminal showing `data/phase5_trace_dump.txt`. Scroll slowly through the span tree: `[CHAIN] phase5_end_to_end → [CHAIN] process_facility → [LLM] anthropic_extract_call ×5 → [CHAT_MODEL] usage={input_tokens=2254, output_tokens≈420} → [TOOL] ground_capability ×36 → [AGENT] validate_facility → [RETRIEVER] lookup_iphs_rules ×8`. | MLflow OTel traces with token usage on every CHAT_MODEL span. |
| 52–60 | Hold final frame on `[RETRIEVER] lookup_iphs_rules` lines showing `capability_name=orthopedic_surgery_services matched_rule_ids=['R01', 'R02']`. | Closes the loop: the validator's per-capability rule lookup is observable in the trace. |

## Optional inserts (use only if you have time slack)

- 2-second flash of `agent/calibrate.py` `IsotonicBinaryClassifier` class definition between t=14 and t=22 if you want to credit the sklearn wrapper specifically.
- 2-second flash of `requirements.txt` showing the pinned versions of `mlflow==3.11.1`, `mapie==1.3.0`, `instructor==1.15.1`, `pydantic==2.13.3` between t=22 and t=30 if rubric-time emphasis on dep hygiene matters.

## Capture settings

- Recorder: QuickTime / OBS / Loom — any 1080p+ at ≥ 30 fps
- Editor zoom level: ≥ 130% so code reads on small screens
- Cursor highlight: ON
- System audio: OFF (voiceover is pasted in post)
- Cut to exactly 60 s; over-shoot by ~5 s during capture and trim on either end.

## Post-record

- Replace voiceover with `tech_video_script.md` narration (record separately for cleaner audio)
- Export 1080p mp4, ≤ 100 MB
- Filename: `agentic-healthcare-maps_tech_60s.mp4`
- Drop into the submission portal alongside the demo video
