"""Reusable UI building blocks."""
from __future__ import annotations

import streamlit as st

from frontend.services import api_client as api
from frontend.utils.constants import AI_DISCLAIMER, AI_TITLE, CONFIDENCE_NOTE, LIMITATIONS

STATUS_ICON = {"Pending Veterinary Review": "🟡", "Under Veterinary Review": "🔵", "Veterinarian Confirmed": "🟢",
               "Veterinarian Revised": "🟠", "Treatment Approved": "💊", "Follow-up Required": "📅",
               "Completed": "✅", "Rejected / Insufficient Information": "⛔"}


def safe(fn, *args, default=None, **kwargs):
    """Call an API function, show a clean error on failure."""
    try:
        return fn(*args, **kwargs)
    except api.ApiError as e:
        st.error(e.message)
        if e.status == 401:
            st.stop()
        return default


def status_badge(label: str) -> str:
    return f"{STATUS_ICON.get(label, '•')} {label}"


def ai_disclaimer() -> None:
    st.info(f"**{AI_TITLE}**\n\n{AI_DISCLAIMER}")


def show_image(url: str, caption: str = "Uploaded image") -> None:
    data = safe(api.get_bytes, url)
    if data:
        st.image(data, caption=caption, use_container_width=True)


def probability_bars(probs: dict[str, float]) -> None:
    for name, p in probs.items():
        c1, c2 = st.columns([3, 1])
        c1.progress(min(max(p, 0.0), 1.0), text=name)
        c2.write(f"{p:.0%}")


def prediction_card(pred: dict, show_image_flag: bool = True) -> None:
    """AI section. Always clearly separated from veterinary output."""
    st.subheader("🤖 AI Disease Prediction")
    st.caption("AI Prediction – not a diagnosis")
    if pred.get("low_confidence"):
        st.error(pred["low_confidence_message"])
    left, right = st.columns([1, 1])
    with left:
        if show_image_flag:
            show_image(pred["image_url"])
    with right:
        st.metric("Predicted class", pred["predicted_class"])
        st.metric("Model confidence", f"{pred['confidence']:.0%}")
        st.caption(CONFIDENCE_NOTE)
    st.markdown("**Probability breakdown**")
    probability_bars(pred["probabilities"])
    d = pred["disease"]
    st.markdown(f"**Disease category:** {d['category']}")
    st.markdown(f"**Description:** {d['description']}")
    if d["reference_symptoms"]:
        st.markdown("**Reference symptoms**")
        st.markdown("\n".join(f"- {s}" for s in d["reference_symptoms"]))
    st.info(f"**{pred['care_suggestion_title']}**\n\n{pred['care_suggestion']}")
    st.markdown(f"**Status:** {status_badge(pred['status_label'])}")
    with st.expander("Important limitations"):
        st.markdown("\n".join(f"- {x}" for x in LIMITATIONS))


def veterinary_section(review: dict | None) -> None:
    """Veterinarian output - separate from AI output."""
    st.subheader("🩺 Veterinarian Assessment")
    if not review:
        st.info("Pending Veterinary Review. Your veterinarian has not issued a diagnosis yet.")
        return
    st.success(f"**{review['diagnosis']}** ({'Veterinarian Confirmed' if review['diagnosis_action'] == 'confirmed' else 'Veterinarian Revised'})")
    st.caption(f"By {review['veterinarian_name']} · License: {review['license_info'] or 'n/a'} · {review['reviewed_at'][:16]}")
    if review.get("clinical_assessment"):
        st.markdown(f"**Assessment:** {review['clinical_assessment']}")
    if review.get("treatment_plan"):
        st.markdown(f"**Treatment plan:** {review['treatment_plan']}")
    if review.get("prescription"):
        st.markdown("#### 💊 Veterinary Prescription")
        st.table({"Medication": [review["prescription"]], "Dosage": [review["dosage"]],
                  "Frequency": [review["frequency"]], "Duration": [review["duration"]]})
    for label, key in (("Additional instructions", "additional_instructions"), ("Comments", "veterinary_comments")):
        if review.get(key):
            st.markdown(f"**{label}:** {review[key]}")
    if review.get("follow_up_date"):
        st.markdown(f"**Follow-up date:** {review['follow_up_date'][:10]}")
