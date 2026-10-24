import json

import pandas as pd
import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api


def render() -> None:
    st.title("🛠️ Administrator Dashboard")
    tabs = st.tabs(["Overview", "Users", "Records", "Knowledge & medication", "Model", "Logs & notifications"])
    with tabs[0]:
        s = safe(api.get, "/api/admin/statistics", default={})
        if s:
            keys = ["total_users", "total_farmers", "total_veterinarians", "total_poultry", "total_predictions",
                    "pending_reviews", "confirmed_diagnoses"]
            cols = st.columns(4)
            for i, k in enumerate(keys):
                cols[i % 4].metric(k.replace("_", " ").title(), s[k])
            st.markdown("**Disease distribution (AI predictions)**")
            st.bar_chart(pd.Series(s["disease_distribution"]))
            st.markdown("**System activity**")
            st.dataframe(pd.DataFrame(s["recent_activity"]), hide_index=True, use_container_width=True)
    with tabs[1]:
        role = st.selectbox("Role", ["all", "farmer", "veterinarian", "admin"])
        users = safe(api.get, "/api/admin/users", role=None if role == "all" else role, default=[])
        st.dataframe(pd.DataFrame(users)[["user_id", "full_name", "email", "role", "license_number", "is_active"]]
                     if users else pd.DataFrame(), hide_index=True, use_container_width=True)
        if users:
            sel = st.selectbox("User", [f"{u['user_id']} – {u['full_name']}" for u in users])
            uid = int(sel.split(" – ")[0])
            c1, c2 = st.columns(2)
            if c1.button("Activate"):
                safe(api.put, f"/api/admin/users/{uid}", json={"is_active": True}); st.rerun()
            if c2.button("Deactivate"):
                safe(api.put, f"/api/admin/users/{uid}", json={"is_active": False}); st.rerun()
        with st.expander("Create user"):
            with st.form("cu"):
                n, e, p = st.text_input("Full name"), st.text_input("Email"), st.text_input("Password", type="password")
                r = st.selectbox("Role", ["farmer", "veterinarian", "admin"], key="cur")
                lic = st.text_input("License (veterinarians)")
                if st.form_submit_button("Create"):
                    if safe(api.post, "/api/admin/users", json={"full_name": n, "email": e, "password": p, "role": r,
                                                                 "license_number": lic or None}):
                        st.success("User created.")
    with tabs[2]:
        st.markdown("**Poultry records**")
        st.dataframe(pd.DataFrame(safe(api.get, "/api/admin/poultry", default=[])), hide_index=True, use_container_width=True)
        st.markdown("**Predictions**")
        preds = safe(api.get, "/api/admin/predictions", default=[])
        st.dataframe(pd.DataFrame([{k: p[k] for k in ("case_id", "poultry_code", "predicted_class", "confidence",
                                                      "status_label", "created_at")} for p in preds]),
                     hide_index=True, use_container_width=True)
    with tabs[3]:
        for d in safe(api.get, "/api/diseases", default=[]):
            with st.expander(f"{d['disease_name']} ({d['category']})"):
                st.write(d["description"]); st.write("Symptoms:", ", ".join(d["reference_symptoms"]))
                st.write("Care:", d["general_care"]); st.write("Referral:", d["referral_guidance"])
                for m in d["medication_reference"]:
                    st.caption(f"💊 {m['medicine_name']} ({m['category']}) – {m['usage_notes']}")
        with st.expander("Add medication reference (general info only – no dosage)"):
            with st.form("addmed"):
                dc = st.selectbox("Disease", ["Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"])
                nm, cat, nt = st.text_input("Medicine / category name"), st.text_input("Category"), st.text_area("Usage notes")
                if st.form_submit_button("Add"):
                    if safe(api.post, "/api/admin/medications", json={"disease_class": dc, "medicine_name": nm,
                                                                       "category": cat, "usage_notes": nt}):
                        st.success("Added.")
    with tabs[4]:
        m = safe(api.get, "/api/admin/model", default={})
        st.metric("Model available", "Yes" if m.get("model_available") else "No")
        if m.get("metadata"):
            st.json(m["metadata"])
        ev = m.get("evaluation")
        if ev:
            st.metric("Test accuracy", f"{ev['accuracy']:.1%}")
            st.json({"macro": ev["macro"], "weighted": ev["weighted"]})
            st.dataframe(pd.DataFrame(ev["per_class"]).T)
            st.markdown("**Confusion matrix**")
            st.dataframe(pd.DataFrame(ev["confusion_matrix"], index=ev["class_order"], columns=ev["class_order"]))
        else:
            st.info(m.get("evaluation_message") or "Model evaluation results are not yet available.")
    with tabs[5]:
        logs = safe(api.get, "/api/admin/logs", limit=300, default=[])
        st.dataframe(pd.DataFrame(logs), hide_index=True, use_container_width=True)
        with st.form("bc"):
            t, msg = st.text_input("Title"), st.text_area("Message")
            r = st.selectbox("Audience", ["everyone", "farmer", "veterinarian", "admin"])
            if st.form_submit_button("Send notification"):
                if safe(api.post, "/api/admin/notifications/broadcast",
                        json={"title": t, "message": msg, "role": None if r == "everyone" else r}):
                    st.success("Sent.")
