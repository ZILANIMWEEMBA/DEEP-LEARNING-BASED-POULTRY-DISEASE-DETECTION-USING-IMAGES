import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api


def render() -> None:
    st.title("💬 Veterinary Consultation")
    rows = safe(api.get, "/api/predictions", default=[])
    if not rows:
        st.info("No cases yet. Upload an image first.")
        return
    labels = [f"{r['case_id']} – {r['predicted_class']} ({r['status_label']})" for r in rows]
    pid = rows[labels.index(st.selectbox("Case", labels))]["prediction_id"]
    for m in safe(api.get, "/api/consultations", prediction_id=pid, default=[]):
        with st.chat_message("user" if m["sender_role"] == "farmer" else "assistant"):
            st.markdown(f"**{m['sender_name']}** ({m['sender_role']}) · {m['created_at'][:16]}")
            st.write(m["message"])
    with st.form("msg"):
        text = st.text_area("Message to your veterinarian")
        req = st.checkbox("This is a request for veterinary review", value=True)
        if st.form_submit_button("Send") and text.strip():
            if safe(api.post, "/api/consultations", json={"prediction_id": pid, "message": text, "is_request": req}):
                st.rerun()
