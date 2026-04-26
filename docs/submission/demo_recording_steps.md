# Demo recording steps — 60s

Step-by-step capture instructions for the **demo video** (social-impact angle). Pair with the voiceover in `demo_video_script.md`.

**Hero record:** `c616c9769f2afbd7` — Dr. Pratik Dhabalia Joint Replacement.
**Total target wall clock:** 60 seconds at normal speaking pace.

## Pre-recording (do once, before you hit record)

1. Open one terminal in the project root with the venv active:
   ```bash
   cd ~/Documents/Agentic-Healthcare-Maps
   source .venv/bin/activate
   ```
2. Pre-launch Streamlit so it's already warm:
   ```bash
   streamlit run eval/citation_demo.py --server.headless true --server.port 8501
   ```
   Then open `http://localhost:8501` in a clean browser tab. Resize the window to ~1280×800. Pick `c616c9769f2afbd7` from the sidebar before you start recording so the demo loads instantly.
3. Open `artifacts/eval/dashboard.html` in a second browser tab.
4. Have `data/phase5_citation_preview.txt` open in a text viewer for an optional close-up insert.
5. Close all unrelated windows. Mute notifications. Use a clean OS theme.

## Recording sequence (in order)

| t (s) | Action | Notes |
|---|---|---|
| 0–6   | **Hook**: Cut to the Streamlit page already loaded on `c616c9769f2afbd7`. The `Dr. Pratik Dhabalia Joint Replacement` heading and the four metric tiles (`self_consistency 1.00`, `source_completeness 0.68`, `iphs_alignment 0.50`, `blended_score 0.73`) should be on screen. | If your screen recorder needs a click to start — click anywhere outside the cards. |
| 6–18  | Pan / scroll slowly to the right column. Hover over the **`orthopedic_surgery_services`** card. Show the YELLOW badge, the `iphs_alignment=0.00` row, the prediction set `{claimed, not_claimed}`. | This is the per-capability discrimination beat. |
| 18–28 | Click the `R01` expander inside that card. The flag text (*"Surgical services claimed without an anaesthesiology provider…"*) and the citation (*"IPHS 2022 Vol II — FRU CHC essential specialists list…"*) reveal. Wait 2 s, then click `R02`. | **Do not** rush this — the citation reveal is the rubric beat for "Discovery & Verification." |
| 28–38 | Scroll up briefly to show **`fracture_clinic_services`** card right next to the surgery cards. iphs_alignment=1.00, no rule expanders. Verbal contrast ("same facility, three sibling claims unflagged"). | Visual proof of per-capability discrimination. |
| 38–48 | Scroll the source-text panel on the left so the highlighted `orthopedicSurgery` and `Knee replacement surgery` evidence quotes are visible. Briefly hover. | Evidence grounding (rapidfuzz ≥ 0.95) becomes visible. |
| 48–58 | Cut to second tab: `artifacts/eval/dashboard.html`. Scroll quickly through the Phase 2/3/4/5 sections; show the **0.9286 empirical coverage** row in Phase 3 and the **8/101 violations** row in Phase 4. | Aggregate proof. |
| 58–60 | Hold on the dashboard's "Generated 2026-04-26" timestamp. End frame. | Closes the loop. |

## Optional inserts (use only if you have time slack)

- 2-second close-up on `data/phase5_citation_preview.txt` showing the verbatim `evidence_quote` lines next to the rule violations. Drop it between t=18 and t=28 if the citation expanders feel too text-heavy on camera.

## Capture settings

- Recorder: QuickTime / OBS / Loom — any 1080p+ at ≥ 30 fps
- Cursor highlight: ON
- System audio: OFF (voiceover is pasted in post)
- Cut down to exactly 60 s in the editor; over-shoot by ~5 s during capture and trim on either end.

## Post-record

- Replace voiceover with `demo_video_script.md` narration (record separately for cleaner audio)
- Export 1080p mp4, ≤ 100 MB
- Filename: `agentic-healthcare-maps_demo_60s.mp4`
- Drop into the submission portal alongside the README and the `project_summary.md`
