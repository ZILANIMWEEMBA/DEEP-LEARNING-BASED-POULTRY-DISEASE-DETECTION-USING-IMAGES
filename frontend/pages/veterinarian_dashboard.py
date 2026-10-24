import pandas as pd
import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    st.title(f"🩺 Welcome, Dr. {st.session_state['user']['full_name']}")
    s = safe(api.get, "/api/veterinary/stats", default={})
    c = st.columns(5)
    for col, (label, key) in zip(c, [("Pending", "pending"), ("Under review", "under_review"), ("Confirmed", "confirmed"),
                                     ("Revised", "revised"), ("Follow-up", "follow_up")]):
        col.metric(label, s.get(key, 0))
    flt = st.selectbox("Filter", ["All", "Pending Review", "Under Review", "Diagnosis Confirmed", "Diagnosis Revised",
                                  "Treatment Issued", "Follow-up Required", "Completed"])
    cases = safe(api.get, "/api/veterinary/cases", status=None if flt == "All" else flt, default=[])
    if not cases:
        st.info("No cases in this view.")
        return
    st.dataframe(pd.DataFrame([{"Case": c["case_id"], "Farmer": c["farmer"], "Poultry": c["poultry_id"],
                                "AI prediction": c["ai_prediction"], "Confidence": f"{c['confidence']:.0%}",
                                "Date": c["date"][:16].replace("T", " "), "Status": c["status"]} for c in cases]),
                 use_container_width=True, hide_index=True)
    sel = st.selectbox("Open case", [c["case_id"] for c in cases])
    if st.button("Open case for review", type="primary"):
        nav_to("veterinary_review", selected_prediction=next(c["prediction_id"] for c in cases if c["case_id"] == sel))
