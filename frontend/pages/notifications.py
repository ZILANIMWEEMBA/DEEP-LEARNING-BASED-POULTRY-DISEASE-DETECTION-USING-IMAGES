import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api


def render() -> None:
    st.title("🔔 Notifications")
    rows = safe(api.get, "/api/notifications", default=[])
    if not rows:
        st.info("No notifications.")
    for n in rows:
        with st.container(border=True):
            st.markdown(f"{'⚪' if n['is_read'] else '🔵'} **{n['title']}** · {n['created_at'][:16].replace('T', ' ')}")
            st.write(n["message"])
            if not n["is_read"] and st.button("Mark as read", key=f"n{n['notification_id']}"):
                safe(api.put, f"/api/notifications/{n['notification_id']}/read")
                st.rerun()
