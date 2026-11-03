import html
from io import BytesIO

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from frontend.components.ui import ai_disclaimer, safe
from frontend.services import api_client as api


def _pdf_value(value: object) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, dict):
        return "<br/>".join(
            f"<b>{html.escape(str(key).replace('_', ' ').title())}:</b> {_pdf_value(item)}"
            for key, item in value.items()
            if item is not None
        )
    if isinstance(value, (list, tuple)):
        return "<br/>".join(f"- {_pdf_value(item)}" for item in value) or "None"
    if isinstance(value, float) and 0 <= value <= 1:
        return f"{value:.0%}"
    return html.escape(str(value)).replace("\n", "<br/>")


def _report_pdf(title: str, content: dict, image_bytes: bytes | None = None) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=title,
    )
    styles = getSampleStyleSheet()
    styles["BodyText"].alignment = TA_LEFT
    story = [Paragraph(html.escape(title), styles["Title"]), Spacer(1, 12)]
    rows = [[Paragraph("<b>Field</b>", styles["BodyText"]),
             Paragraph("<b>Details</b>", styles["BodyText"])]]
    for key, value in content.items():
        if key in {"report_type", "title", "image"}:
            continue
        rows.append([
            Paragraph(html.escape(key.replace("_", " ").title()), styles["BodyText"]),
            Paragraph(_pdf_value(value), styles["BodyText"]),
        ])
    table = LongTable(rows, colWidths=[1.65 * inch, 5.55 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf1f8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324d")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8d2dc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    if image_bytes:
        story.extend([
            Spacer(1, 16),
            Paragraph("Uploaded Poultry Image", styles["Heading2"]),
            Spacer(1, 6),
            Image(BytesIO(image_bytes), width=6.9 * inch, height=4.2 * inch, kind="proportional"),
        ])
    document.build(story)
    return buffer.getvalue()


def _case_picker() -> int | None:
    rows = safe(api.get, "/api/predictions", default=[])
    if not rows:
        st.info("No cases yet.")
        return None
    ids = [r["prediction_id"] for r in rows]
    default = st.session_state.get("selected_prediction")
    idx = ids.index(default) if default in ids else 0
    label = st.selectbox("Case", [f"{r['case_id']} – {r['predicted_class']}" for r in rows], index=idx)
    return rows[[f"{r['case_id']} – {r['predicted_class']}" for r in rows].index(label)]["prediction_id"]


def _kv(content: dict, skip: set[str]) -> None:
    for k, v in content.items():
        if k in skip or v in (None, "", [], {}):
            continue
        label = k.replace("_", " ").title()
        if k == "confidence":
            st.markdown(f"**{label}:** {v:.0%}")
        elif isinstance(v, dict):
            st.markdown(f"**{label}**")
            for kk, vv in v.items():
                st.markdown(f"- {kk}: {vv:.0%}" if isinstance(vv, float) else f"- {kk}: {vv}")
        elif isinstance(v, list):
            st.markdown(f"**{label}**")
            for x in v:
                st.markdown("- " + (", ".join(f"{a}: {b}" for a, b in x.items()) if isinstance(x, dict) else str(x)))
        else:
            st.markdown(f"**{label}:** {v}")


def render() -> None:
    st.title("📄 Reports")
    pid = _case_picker()
    if pid is None:
        return
    reports = safe(api.get, "/api/reports", prediction_id=pid, default=[])
    ai = next((r for r in reports if r["report_type"] == "ai"), None)
    vet = next((r for r in reports if r["report_type"] == "veterinary"), None)
    t1, t2 = st.tabs(["🤖 AI Report", "🩺 Veterinary Report"])
    with t1:
        if ai:
            ai_disclaimer()
            _kv(ai["content"], {"report_type", "disclaimer", "disclaimer_title"})
            st.download_button("Download AI report (PDF)", _report_pdf("AI Decision-Support Report", ai["content"]),
                               file_name=f"ai_report_{ai['content']['case_id']}.pdf", mime="application/pdf")
    with t2:
        if vet:
            _kv(vet["content"], {"report_type", "image"})
            image_bytes = api.get_bytes(vet["content"]["image"])
            st.download_button(
                "Download veterinary report (PDF)",
                _report_pdf("Veterinary Report", vet["content"], image_bytes),
                file_name=f"vet_report_{vet['content']['case_id']}.pdf",
                mime="application/pdf",
            )
        else:
            st.info("No veterinary report yet. It becomes available after a veterinarian reviews the case.")
