"""Streamlit entry point.  Run:  streamlit run frontend/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from frontend.pages import (admin_dashboard, consultations, farmer_dashboard, history, login, notifications,  # noqa: E402
                            poultry, prediction, profile, register, reports, upload_image,
                            veterinarian_dashboard, veterinary_review)
from frontend.utils.state import init_state, is_logged_in, logout, nav_to  # noqa: E402

st.set_page_config(page_title="PoultryDx AI", page_icon="🐔", layout="wide")
init_state()

PAGES = {
    "login": login.render, "register": register.render,
    "farmer_dashboard": farmer_dashboard.render, "profile": profile.render, "poultry": poultry.render,
    "upload_image": upload_image.render, "prediction": prediction.render, "history": history.render,
    "consultations": consultations.render, "reports": reports.render, "notifications": notifications.render,
    "veterinarian_dashboard": veterinarian_dashboard.render, "veterinary_review": veterinary_review.render,
    "admin_dashboard": admin_dashboard.render,
}
MENUS = {
    "farmer": [("Dashboard", "farmer_dashboard"), ("My Profile", "profile"), ("My Poultry", "poultry"),
               ("Detect Disease", "upload_image"), ("Prediction History", "history"),
               ("Veterinary Consultation", "consultations"), ("Reports", "reports"), ("Notifications", "notifications")],
    "veterinarian": [("Dashboard", "veterinarian_dashboard"), ("Case Review", "veterinary_review"),
                     ("Reports", "reports"), ("Notifications", "notifications"), ("My Profile", "profile")],
    "admin": [("Dashboard", "admin_dashboard"), ("Notifications", "notifications"), ("My Profile", "profile")],
}
PUBLIC = {"login", "register"}
ROLE_PAGES = {r: {p for _, p in m} | ({"prediction"} if r == "farmer" else set()) for r, m in MENUS.items()}


def main() -> None:
    page = st.session_state["page"]
    if not is_logged_in():
        PAGES.get(page if page in PUBLIC else "login", login.render)()
        return
    user = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"### 🐔 Poultry Health\n**{user['full_name']}**  \n_{user['role'].title()}_")
        for label, target in MENUS[user["role"]]:
            if st.button(label, key=f"nav_{target}", use_container_width=True):
                nav_to(target)
        if st.button("Logout", use_container_width=True):
            logout(); st.rerun()
        st.caption("AI is an assistant. The veterinarian is the final clinical authority.")
    # route guard: a user can only reach pages for their own role
    if page not in ROLE_PAGES[user["role"]]:
        page = MENUS[user["role"]][0][1]
        st.session_state["page"] = page
    PAGES[page]()


main()
