import streamlit as st


def init_state() -> None:
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("auth_view", "login")

    query_page = st.query_params.get("page") if hasattr(st, "query_params") else None
    if query_page:
        st.session_state["page"] = str(query_page)
    else:
        st.session_state.setdefault("page", "login")


def is_logged_in() -> bool:
    return bool(st.session_state.get("token") and st.session_state.get("user"))


def nav_to(page: str, **kw) -> None:
    st.session_state["page"] = page
    st.query_params["page"] = page if hasattr(st, "query_params") else None
    for k, v in kw.items():
        st.session_state[k] = v
    st.rerun()


def logout() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    if hasattr(st, "query_params"):
        st.query_params.clear()
    init_state()
