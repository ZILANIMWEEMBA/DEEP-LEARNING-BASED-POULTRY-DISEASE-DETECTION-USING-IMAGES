import io

import streamlit as st
from PIL import Image

from frontend.components.ui import ai_disclaimer, safe
from frontend.services import api_client as api
from frontend.utils.state import nav_to

MAX_MB = 20


def render() -> None:
    st.title("🔍 Detect Disease")
    ai_disclaimer()
    poultry = safe(api.get, "/api/poultry", default=[])
    if not poultry:
        st.info("Please register your poultry first.")
        if st.button("Register poultry"):
            nav_to("poultry")
        return
    opts = {f"{p['poultry_code']} – {p['poultry_type']} ({p['flock_size']})": p["poultry_id"] for p in poultry}
    chosen = st.selectbox("Select poultry", list(opts))
    file = st.file_uploader("Upload a clear photo (JPG, JPEG or PNG, max 20 MB)", type=["jpg", "jpeg", "png"])
    symptoms = st.text_area("Symptoms you noticed (optional)", placeholder="e.g. bloody droppings, not eating")
    obs = st.text_area("Other observations (optional)")
    valid = False
    if file is not None:
        data = file.getvalue()
        if len(data) > MAX_MB * 1024 * 1024:
            st.error(f"Image is too large. Maximum size is {MAX_MB} MB.")
        else:
            try:
                im = Image.open(io.BytesIO(data)); im.load()
                if min(im.size) < 64:
                    st.error("Image is too small (minimum 64 pixels per side).")
                else:
                    st.image(im, caption=f"Preview ({im.size[0]}×{im.size[1]})", use_container_width=True)
                    valid = True
            except Exception:  # noqa: BLE001
                st.error("This file is not a readable image.")
    if st.button("Detect Disease", type="primary", disabled=not valid, use_container_width=True):
        with st.spinner("Analysing image…"):
            try:
                res = api.upload_prediction(opts[chosen], file.name, file.getvalue(),
                                            file.type or "image/jpeg", symptoms, obs)
            except api.ApiError as e:
                st.error(e.message)
                return
        nav_to("prediction", selected_prediction=res["prediction_id"])
