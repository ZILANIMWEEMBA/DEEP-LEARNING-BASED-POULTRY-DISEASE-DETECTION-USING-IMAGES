import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api


def render() -> None:
    st.title("👤 My Profile")
    u = safe(api.get, "/api/users/me")
    if not u:
        return
    st.caption(f"Role: {u['role']} · Email: {u['email']}")
    with st.form("prof"):
        name = st.text_input("Full name", u["full_name"])
        phone = st.text_input("Phone", u["contact_number"] or "")
        loc = st.text_input("Location", u["location"] or "")
        lic = st.text_input("License number", u["license_number"] or "") if u["role"] == "veterinarian" else None
        st.markdown("**Change password (optional)**")
        cur = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        if st.form_submit_button("Save"):
            body = {"full_name": name, "contact_number": phone, "location": loc}
            if lic is not None:
                body["license_number"] = lic
            if new:
                body.update(current_password=cur, new_password=new)
            res = safe(api.put, "/api/users/me", json=body)
            if res:
                st.session_state["user"] = res
                st.success("Profile updated.")
