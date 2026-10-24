import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api

TYPES = ["Chicken", "Duck", "Turkey", "Guinea fowl", "Other"]
PRODUCTION = ["Layer", "Broiler", "Dual purpose", "Breeder", "Backyard"]


def render() -> None:
    st.title("🐔 My Poultry")
    with st.expander("➕ Register new poultry / flock", expanded=False):
        with st.form("new_poultry"):
            t = st.selectbox("Poultry type", TYPES)
            breed = st.text_input("Breed")
            age = st.number_input("Age (weeks)", 0, 500, 4)
            size = st.number_input("Flock size", 1, 1_000_000, 10)
            prod = st.selectbox("Production type", PRODUCTION)
            hist = st.text_area("Health history (vaccinations, past illness)")
            if st.form_submit_button("Save", use_container_width=True):
                if safe(api.post, "/api/poultry", json={"poultry_type": t, "breed": breed or None, "age": int(age),
                                                         "flock_size": int(size), "production_type": prod,
                                                         "health_history": hist or None}):
                    st.success("Poultry registered.")
                    st.rerun()
    for p in safe(api.get, "/api/poultry", default=[]):
        with st.container(border=True):
            st.markdown(f"**{p['poultry_code']}** · {p['poultry_type']} ({p['breed'] or 'breed n/a'})")
            st.caption(f"Age: {p['age']} weeks · Flock size: {p['flock_size']} · {p['production_type'] or ''}")
            with st.expander("Edit"):
                with st.form(f"edit{p['poultry_id']}"):
                    size = st.number_input("Flock size", 1, 1_000_000, p["flock_size"], key=f"s{p['poultry_id']}")
                    age = st.number_input("Age (weeks)", 0, 500, p["age"] or 0, key=f"a{p['poultry_id']}")
                    hist = st.text_area("Health history", p["health_history"] or "", key=f"h{p['poultry_id']}")
                    if st.form_submit_button("Update"):
                        if safe(api.put, f"/api/poultry/{p['poultry_id']}",
                                json={"flock_size": int(size), "age": int(age), "health_history": hist}):
                            st.success("Updated."); st.rerun()
            if st.button("Delete", key=f"del{p['poultry_id']}"):
                try:
                    api.delete(f"/api/poultry/{p['poultry_id']}")
                    st.rerun()
                except api.ApiError as e:
                    st.error(e.message)
