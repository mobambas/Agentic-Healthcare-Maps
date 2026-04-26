"""Throwaway Streamlit preview of the citation surface that Lovable will render.

Loads the existing JSONL outputs and the IPHS rulebook, lets the user pick a
source_record_id, and renders the FacilityClaim source text on the left with
evidence quotes highlighted, alongside per-capability trust cards on the right.

Run:
    streamlit run eval/citation_demo.py

Treat this file as an eval artifact, not a deliverable. Lovable / React owns
the production surface; the trace.py FastAPI route is the canonical contract.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXTRACT_PATH = ROOT / "data" / "phase2_extractions.jsonl"
TRUST_PATH = ROOT / "data" / "phase3_trust_scores.jsonl"
VALIDATIONS_PATH = ROOT / "data" / "phase4_validations.jsonl"
RULES_PATH = ROOT / "data" / "iphs_rules.yaml"

BADGE_COLORS = {"green": "#22c55e", "yellow": "#eab308", "red": "#ef4444"}


@st.cache_data
def load_jsonl_index(path: str) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    return {
        record["source_record_id"]: record
        for record in (json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
    }


@st.cache_data
def load_rules(path: str) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        rules = yaml.safe_load(fh) or []
    return {rule["id"]: rule for rule in rules}


def highlight_source(source_text: str, capability_scores: list[dict]) -> str:
    spans: list[tuple[int, int, str]] = []
    for cap in capability_scores:
        quote = cap.get("evidence_quote") if "evidence_quote" in cap else None
        if quote is None:
            continue
        for match in re.finditer(re.escape(quote), source_text):
            spans.append((match.start(), match.end(), cap.get("badge", "yellow")))
    if not spans:
        return f"<pre style='white-space:pre-wrap'>{html.escape(source_text)}</pre>"
    spans.sort()
    merged: list[tuple[int, int, str]] = []
    for start, end, badge in spans:
        if merged and start < merged[-1][1]:
            continue
        merged.append((start, end, badge))
    out: list[str] = []
    cursor = 0
    for start, end, badge in merged:
        out.append(html.escape(source_text[cursor:start]))
        color = BADGE_COLORS.get(badge, "#cbd5e1")
        out.append(
            f"<mark style='background:{color}33;border-bottom:2px solid {color};padding:0 2px'>"
            f"{html.escape(source_text[start:end])}</mark>"
        )
        cursor = end
    out.append(html.escape(source_text[cursor:]))
    return f"<pre style='white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:13px'>{''.join(out)}</pre>"


def render_capability_card(cap_score: dict, validation: dict | None, rules: dict[str, dict]) -> None:
    badge = cap_score.get("badge", "yellow")
    color = BADGE_COLORS.get(badge, "#cbd5e1")
    name = cap_score["name"]
    iphs = cap_score.get("iphs_alignment", 1.0)
    raw = cap_score.get("raw_score", 0.0)
    cal = cap_score.get("calibrated_score", 0.0)
    pset = cap_score.get("prediction_set", [])
    violated = cap_score.get("violated_rule_ids", [])
    sc = cap_score.get("confidence_self_consistency", 0.0)

    with st.container(border=True):
        cols = st.columns([4, 1])
        cols[0].markdown(f"**`{name}`**")
        cols[1].markdown(
            f"<span style='background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px'>"
            f"{badge.upper()}</span>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"self_consistency={sc:.2f} · iphs_alignment={iphs:.2f} · "
            f"raw={raw:.2f} · calibrated={cal:.2f} · "
            f"prediction_set={{{', '.join(pset) if pset else '∅'}}}"
        )
        if validation:
            quote = ""
            for ev in validation.get("supporting_evidence", []):
                m = re.search(r"evidence_quote=(['\"].*?['\"])", ev)
                if m:
                    quote = m.group(1)
                    break
            if quote:
                st.markdown(f"_evidence:_ {quote}")
        if validated_quote := next(
            (cap.get("evidence_quote") for cap in [cap_score] if cap.get("evidence_quote")), None
        ):
            st.markdown(f"_quote:_ {validated_quote!r}")
        if violated:
            for rule_id in violated:
                rule = rules.get(rule_id, {})
                with st.expander(f"⚠️  {rule_id} — {rule.get('severity', '?').upper()}", expanded=False):
                    st.markdown(f"**Rule:** {rule.get('flag_text', '(no description)')}")
                    st.markdown(f"**Citation:** `{rule.get('citation', '(uncited)')}`")
                    st.markdown(f"**Framework:** {rule.get('framework', '?')}")
        if validation and validation.get("reasoning"):
            st.caption(validation["reasoning"])


def main() -> None:
    st.set_page_config(page_title="Citation surface preview", layout="wide")
    st.title("Phase 5 — Citation Surface Preview")
    st.caption(
        "Each capability is shown as a card with its alignment score, prediction set, "
        "violated IPHS rules, and the verbatim source quote that grounds the claim. "
        "Badges are conservative at 30-record calibration scale; the per-capability "
        "iphs_alignment and violated_rule_ids are the headline trust signal."
    )

    extractions = load_jsonl_index(str(EXTRACT_PATH))
    trust = load_jsonl_index(str(TRUST_PATH))
    validations = load_jsonl_index(str(VALIDATIONS_PATH))
    rules = load_rules(str(RULES_PATH))

    if not trust:
        st.error(f"Run eval/phase3_calibration.py first; {TRUST_PATH.name} is missing.")
        return

    sids = sorted(trust.keys())
    facility_label = {
        sid: f"{sid}  ({trust[sid].get('facility_name', '')})" for sid in sids
    }
    default_idx = sids.index("c616c9769f2afbd7") if "c616c9769f2afbd7" in sids else 0
    sid = st.sidebar.selectbox(
        "source_record_id",
        sids,
        index=default_idx,
        format_func=lambda x: facility_label[x],
    )
    rec_trust = trust[sid]
    rec_extr = extractions.get(sid, {})
    rec_validations = (validations.get(sid) or {}).get("validations", [])
    validation_by_cap = {v["capability_name"]: v for v in rec_validations}

    st.subheader(rec_trust.get("facility_name", sid))
    summary_cols = st.columns(4)
    summary_cols[0].metric("self_consistency", f"{rec_trust['self_consistency_component']:.2f}")
    summary_cols[1].metric("source_completeness", f"{rec_trust['source_completeness_component']:.2f}")
    summary_cols[2].metric("iphs_alignment", f"{rec_trust['iphs_alignment_component']:.2f}")
    summary_cols[3].metric("blended_score", f"{rec_trust['blended_score']:.2f}")

    bc = rec_trust.get("badge_counts", {})
    st.caption(
        f"badge counts:  green={bc.get('green', 0)}  ·  yellow={bc.get('yellow', 0)}  ·  red={bc.get('red', 0)}"
    )

    body_cols = st.columns([1, 1])
    with body_cols[0]:
        st.markdown("##### Source text (evidence-highlighted)")
        capability_payload = [
            {
                **cap,
                "evidence_quote": next(
                    (
                        c["evidence_quote"]
                        for c in rec_extr.get("claim", {}).get("capabilities", [])
                        if c["name"] == cap["name"]
                    ),
                    None,
                ),
            }
            for cap in rec_trust.get("capability_scores", [])
        ]
        source_text = ""
        for cap in rec_extr.get("claim", {}).get("capabilities", []):
            pass
        # Reconstruct source text from the extraction file's claim.evidence_quotes is a partial view;
        # for highlighting we re-render the tagged blocks from the canonical raw text if available.
        # phase2_extractions.jsonl does not store source_text per record (it was only in gold_labels.jsonl);
        # so we fall back to assembling a faux source from the evidence quotes themselves.
        evidence_strs = [
            f"<{c.get('name')}>: {c.get('evidence_quote', '')}"
            for c in rec_extr.get("claim", {}).get("capabilities", [])
        ]
        st.markdown(
            highlight_source("\n".join(evidence_strs), capability_payload),
            unsafe_allow_html=True,
        )

    with body_cols[1]:
        st.markdown("##### Capability trust cards")
        for cap_score in rec_trust.get("capability_scores", []):
            render_capability_card(
                cap_score,
                validation_by_cap.get(cap_score["name"]),
                rules,
            )


if __name__ == "__main__":
    main()
