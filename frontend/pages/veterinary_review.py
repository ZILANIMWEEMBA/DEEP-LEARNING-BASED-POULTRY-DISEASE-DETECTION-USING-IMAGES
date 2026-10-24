from datetime import date

import streamlit as st

from frontend.components.ui import prediction_card, safe, show_image, veterinary_section
from frontend.services import api_client as api
from frontend.utils.constants import CLASS_NAMES
from frontend.utils.state import nav_to


def render() -> None:
    pid = st.session_state.get("selected_prediction")
    if not pid:
        st.info("Select a case from the dashboard.")
        if st.button("Back to dashboard"):
            nav_to("veterinarian_dashboard")
        return
    if safe(api.post, f"/api/veterinary/cases/{pid}/claim") is None:
        return
    d = safe(api.get, f"/api/veterinary/cases/{pid}")
    if not d:
        return
    case, review = d["case"], d["case"].get("review")
    st.title(f"Case review · {case['case_id']}")

    t1, t2, t3, t4 = st.tabs(["🖼️ Image & AI", "🐔 Poultry & history", "💬 Messages", "📝 Diagnosis & treatment"])
    with t1:
        st.caption("The AI output below is a decision-support suggestion, not a diagnosis.")
        prediction_card(case)
    with t2:
        p, f = d["poultry"], d["farmer"]
        st.markdown(f"**Farmer:** {f['name']} · {f['contact_number'] or 'no phone'} · {f['location'] or ''}")
        st.markdown(f"**Poultry:** {p['poultry_id']} · {p['type']} · {p['breed'] or 'n/a'} · {p['age_weeks']} wks · flock {p['flock_size']} · {p['production_type'] or ''}")
        st.markdown(f"**Health history:** {p['health_history'] or 'none recorded'}")
        if case.get("symptoms"):
            st.markdown(f"**Farmer-reported symptoms:** {case['symptoms']}")
        if case.get("farmer_observations"):
            st.markdown(f"**Farmer observations:** {case['farmer_observations']}")
        st.markdown("**Previous cases for this poultry**")
        st.table([{"Case": h["case_id"], "AI class": h["predicted_class"], "Status": h["status"], "Date": h["date"][:10]}
                  for h in d["poultry_history"]])
    with t3:
        for m in d["consultations"]:
            with st.chat_message("user" if m["role"] == "farmer" else "assistant"):
                st.markdown(f"**{m['sender']}** · {m['created_at'][:16]}"); st.write(m["message"])
        with st.form("vet_msg"):
            txt = st.text_area("Message to farmer")
            if st.form_submit_button("Send") and txt.strip():
                if safe(api.post, "/api/consultations", json={"prediction_id": pid, "message": txt}):
                    st.rerun()
    with t4:
        _review_form(pid, case, review)


def _review_form(pid: int, case: dict, review: dict | None) -> None:
    ai_class = case["predicted_class"]
    st.info(f"AI reference (not a prescription): **{ai_class}** — {case['care_suggestion']}")
    if review:
        veterinary_section(review)
        st.markdown("---\n**Update this review**")
    r = review or {}
    with st.form("review_form"):
        opts = CLASS_NAMES + ["Other (specify below)"]
        default = CLASS_NAMES.index(r["diagnosis"]) if r.get("diagnosis") in CLASS_NAMES else CLASS_NAMES.index(ai_class)
        choice = st.selectbox("Veterinary diagnosis", opts, index=default)
        other = st.text_input("If other, specify diagnosis")
        assessment = st.text_area("Clinical assessment", r.get("clinical_assessment") or "")
        plan = st.text_area("Treatment recommendation", r.get("treatment_plan") or "")
        st.markdown("**Prescription (enter only if clinically appropriate — nothing is pre-filled by the AI)**")
        c1, c2, c3, c4 = st.columns(4)
        med = c1.text_input("Medication", r.get("prescription") or "")
        dose = c2.text_input("Dosage", r.get("dosage") or "")
        freq = c3.text_input("Frequency", r.get("frequency") or "")
        dur = c4.text_input("Duration", r.get("duration") or "")
        instr = st.text_area("Additional instructions", r.get("additional_instructions") or "")
        comments = st.text_area("Veterinarian comments", r.get("veterinary_comments") or "")
        fu = st.checkbox("Schedule follow-up", value=bool(r.get("follow_up_date")))
        fu_date = st.date_input("Follow-up date", value=date.today())
        done = st.checkbox("Mark case as completed")
        submit = st.form_submit_button("Save veterinary review" if not review else "Update review", type="primary")
    if submit:
        diagnosis = other.strip() if choice.startswith("Other") else choice
        if not diagnosis:
            st.error("Please specify the diagnosis."); return
        body = {"diagnosis": diagnosis,
                "diagnosis_action": "confirmed" if diagnosis.lower() == ai_class.lower() else "revised",
                "clinical_assessment": assessment or None, "treatment_plan": plan or None,
                "prescription": med.strip() or None, "dosage": dose or None, "frequency": freq or None,
                "duration": dur or None, "additional_instructions": instr or None,
                "veterinary_comments": comments or None, "mark_completed": done,
                "follow_up_date": f"{fu_date}T00:00:00" if fu else None}
        if review:
            res = safe(api.put, f"/api/veterinary/review/{review['review_id']}", json=body)
        else:
            res = safe(api.post, "/api/veterinary/review", json={**body, "prediction_id": pid})
        if res:
            st.success("Review saved. The farmer has been notified.")
            st.rerun()
    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("Mark: Insufficient information"):
        if safe(api.put, f"/api/veterinary/cases/{pid}/status",
                json={"status": "Rejected / Insufficient Information", "comment": "Please upload a clearer image."}):
            st.rerun()
    if c2.button("⬅ Back to dashboard"):
        nav_to("veterinarian_dashboard")
