import json

import streamlit as st

from frontend.components.ui import ai_disclaimer, safe
from frontend.services import api_client as api


def _case_picker() -> int | None:
    rows = safe(api.get, "/api/predictions", default=[])
    if not rows:
        st.info("No cases yet.")
        return None
    ids = [r["prediction_id"] for r in rows]
    default = st.session_state.get("selected_prediction")
    idx = ids.index(default) if default in ids else 0
    label = st.selectbox("Case", [f"{r['case_id']} – {r['predicted_class']}" for r in rows], index=idx)
    return rows[[f"{r['case_id']} – {r['predicted_class']}" for r in rows].index(label)]["prediction_id"]


def _kv(content: dict, skip: set[str]) -> None:
    for k, v in content.items():
        if k in skip or v in (None, "", [], {}):
            continue
        label = k.replace("_", " ").title()
        if k == "confidence":
            st.markdown(f"**{label}:** {v:.0%}")
        elif isinstance(v, dict):
            st.markdown(f"**{label}**")
            for kk, vv in v.items():
                st.markdown(f"- {kk}: {vv:.0%}" if isinstance(vv, float) else f"- {kk}: {vv}")
        elif isinstance(v, list):
            st.markdown(f"**{label}**")
            for x in v:
                st.markdown("- " + (", ".join(f"{a}: {b}" for a, b in x.items()) if isinstance(x, dict) else str(x)))
        else:
            st.markdown(f"**{label}:** {v}")


def render() -> None:
    st.title("📄 Reports")
    pid = _case_picker()
    if pid is None:
        return
    reports = safe(api.get, "/api/reports", prediction_id=pid, default=[])
    ai = next((r for r in reports if r["report_type"] == "ai"), None)
    vet = next((r for r in reports if r["report_type"] == "veterinary"), None)
    t1, t2 = st.tabs(["🤖 AI Report", "🩺 Veterinary Report"])
    with t1:
        if ai:
            ai_disclaimer()
            _kv(ai["content"], {"report_type", "disclaimer", "disclaimer_title"})
            st.download_button("Download AI report (JSON)", json.dumps(ai["content"], indent=2),
                               file_name=f"ai_report_{ai['content']['case_id']}.json", mime="application/json")
    with t2:
        if vet:
            _kv(vet["content"], {"report_type"})
            st.download_button("Download veterinary report (JSON)", json.dumps(vet["content"], indent=2),
                               file_name=f"vet_report_{vet['content']['case_id']}.json", mime="application/json")
        else:
            st.info("No veterinary report yet. It becomes available after a veterinarian reviews the case.")
