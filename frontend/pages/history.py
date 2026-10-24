import pandas as pd
import streamlit as st

from frontend.components.ui import safe
from frontend.services import api_client as api
from frontend.utils.state import nav_to


def render() -> None:
    st.title("📚 Prediction History")
    rows = safe(api.get, "/api/predictions", default=[])
    if not rows:
        st.info("No predictions yet.")
        return
    df = pd.DataFrame([{"Case": r["case_id"], "Poultry": r["poultry_code"], "AI prediction": r["predicted_class"],
                        "Confidence": f"{r['confidence']:.0%}", "Status": r["status_label"],
                        "Date": r["created_at"][:16].replace("T", " ")} for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True)
    sel = st.selectbox("Open a case", [r["case_id"] for r in rows])
    if st.button("Open case"):
        nav_to("prediction", selected_prediction=next(r["prediction_id"] for r in rows if r["case_id"] == sel))
