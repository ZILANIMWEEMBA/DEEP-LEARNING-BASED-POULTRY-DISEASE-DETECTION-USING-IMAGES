import streamlit as st

from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    st.title("Create an account")
    role = st.radio("I am a", ["Poultry farmer", "Veterinarian"], horizontal=True)
    with st.form("reg"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        phone = st.text_input("Phone number (optional)")
        loc = st.text_input("Location (optional)")
        lic = st.text_input("Professional license / registration number") if role == "Veterinarian" else None
        pw = st.text_input("Password (min 8 characters, letters and numbers)", type="password")
        pw2 = st.text_input("Confirm password", type="password")
        ok = st.form_submit_button("Register", use_container_width=True)
    if ok:
        if pw != pw2:
            st.error("Passwords do not match.")
        else:
            try:
                api.post("/api/auth/register", json={
                    "full_name": name, "email": email, "password": pw, "contact_number": phone or None,
                    "location": loc or None, "role": "veterinarian" if lic is not None else "farmer",
                    "license_number": lic})
                try:
                    res = api.post("/api/auth/login", json={"email": email, "password": pw})
                except api.ApiError as e:
                    st.success("Account created. Please log in.")
                    st.error(e.message)
                    return
                st.session_state["token"], st.session_state["user"] = res["access_token"], res["user"]
                home = {"farmer": "farmer_dashboard", "veterinarian": "veterinarian_dashboard", "admin": "admin_dashboard"}
                nav_to(home[res["user"]["role"]])
            except api.ApiError as e:
                st.error(e.message)
    if st.button("Forgot password?"):
        st.info("Please contact the administrator to reset your password.")
    if st.button("Back to login"):
        nav_to("login")
