import streamlit as st

from frontend.components.ui import ai_disclaimer, prediction_card, safe, veterinary_section
from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    pid = st.session_state.get("selected_prediction")
    if not pid:
        st.info("No case selected.")
        if st.button("Go to history"):
            nav_to("history")
        return
    pred = safe(api.get, f"/api/predictions/{pid}")
    if not pred:
        return
    st.title(f"{pred['case_id']} · {pred['poultry_code']}")
    ai_disclaimer()
    prediction_card(pred)
    st.divider()
    veterinary_section(pred.get("review"))
    st.divider()
    c1, c2, c3 = st.columns(3)
    if c1.button("📨 Request Veterinary Review", use_container_width=True, disabled=pred["review"] is not None):
        if safe(api.post, "/api/consultations", json={"prediction_id": pid, "is_request": True,
                                                       "message": "Please review this case."}):
            st.success("Request sent to veterinarians.")
    if c2.button("📄 View Full Report", use_container_width=True):
        nav_to("reports", selected_prediction=pid)
    if c3.button("🏠 Return to Dashboard", use_container_width=True):
        nav_to("farmer_dashboard")
