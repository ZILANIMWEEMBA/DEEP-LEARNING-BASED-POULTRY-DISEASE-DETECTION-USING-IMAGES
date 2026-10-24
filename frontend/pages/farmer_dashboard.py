import streamlit as st

from frontend.components.ui import safe, status_badge
from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    user = st.session_state["user"]
    st.title(f"Welcome, {user['full_name']}")
    s = safe(api.get, "/api/predictions/summary/me", default={})
    c = st.columns(4)
    c[0].metric("Registered poultry", s.get("registered_poultry", 0))
    c[1].metric("Total predictions", s.get("total_predictions", 0))
    c[2].metric("Pending vet reviews", s.get("pending_reviews", 0))
    c[3].metric("Confirmed diagnoses", s.get("confirmed_diagnoses", 0))
    b1, b2 = st.columns(2)
    if b1.button("🔍 Detect disease", use_container_width=True):
        nav_to("upload_image")
    if b2.button("🐔 My poultry", use_container_width=True):
        nav_to("poultry")
    st.subheader("Recent cases")
    rows = safe(api.get, "/api/predictions", limit=5, default=[])
    if not rows:
        st.info("No cases yet. Register your poultry and upload an image to begin.")
    for p in rows:
        with st.container(border=True):
            a, b, c2 = st.columns([2, 2, 1])
            a.markdown(f"**{p['case_id']}** · {p['poultry_code']}")
            b.write(f"AI: {p['predicted_class']} ({p['confidence']:.0%}) · {status_badge(p['status_label'])}")
            if c2.button("Open", key=f"open{p['prediction_id']}"):
                nav_to("prediction", selected_prediction=p["prediction_id"])
