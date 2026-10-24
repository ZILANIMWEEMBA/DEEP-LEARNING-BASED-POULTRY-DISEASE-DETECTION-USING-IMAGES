import streamlit as st

from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    st.title("Poultry Health Support")
    st.caption("AI-assisted poultry health management with veterinary review")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        ok = st.form_submit_button("Log in", use_container_width=True)
    if ok:
        try:
            res = api.post("/api/auth/login", json={"email": email, "password": password})
        except api.ApiError as e:
            st.error(e.message)
            return
        st.session_state["token"], st.session_state["user"] = res["access_token"], res["user"]
        home = {"farmer": "farmer_dashboard", "veterinarian": "veterinarian_dashboard", "admin": "admin_dashboard"}
        nav_to(home[res["user"]["role"]])
    if st.button("Forgot password?"):
        st.info("Please contact the administrator to reset your password.")
    if st.button("New here? Create an account"):
        nav_to("register")
