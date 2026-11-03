from io import BytesIO

from PIL import Image as PILImage

from frontend.pages.reports import _pdf_value, _report_pdf


def test_report_pdf_formats_nested_values_without_quotes():
    value = {"poultry": {"poultry_id": "POULTRY-4", "flock_size": 30},
             "probabilities": {"Healthy": 0.1, "Coccidiosis": 0.9}}

    formatted = _pdf_value(value)

    assert '"' not in formatted
    assert "Poultry Id:" in formatted and "POULTRY-4" in formatted
    assert "Flock Size:" in formatted and "30" in formatted
    assert "Healthy:</b> 10%" in formatted and "Coccidiosis:</b> 90%" in formatted


def test_veterinary_report_pdf_embeds_uploaded_image():
    image_buffer = BytesIO()
    PILImage.new("RGB", (64, 64), color="green").save(image_buffer, format="JPEG")

    pdf = _report_pdf(
        "Veterinary Report",
        {"case_id": "CASE-4", "image": "/api/predictions/4/image", "confirmed_diagnosis": "Healthy"},
        image_buffer.getvalue(),
    )

    assert pdf.startswith(b"%PDF-")
    assert b"/Subtype /Image" in pdf
