import io

from PIL import Image

from tests.conftest import make_image, upload


def test_prediction_flow(client, farmer, poultry_id):
    r = upload(client, farmer, poultry_id)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["predicted_class"] == "Coccidiosis" and abs(d["confidence"] - 0.91) < 1e-6
    assert d["label"] == "AI Prediction"
    assert d["care_suggestion_title"] == "AI Care Suggestion – Not a Prescription"
    assert "qualified veterinarian" in d["disclaimer"]
    assert d["status_label"] == "Pending Veterinary Review" and d["review"] is None
    assert d["case_id"].startswith("CASE-") and d["poultry_code"].startswith("POULTRY-")
    assert d["disease"]["category"] == "Parasitic"
    assert d["low_confidence"] is False
    # no dosage/prescription is produced by the AI
    assert "dosage" not in str(d).lower()
    # history + image access
    assert len(client.get("/api/predictions", headers=farmer).json()) == 1
    assert client.get(d["image_url"], headers=farmer).status_code == 200
    assert client.get("/api/predictions/summary/me", headers=farmer).json()["pending_reviews"] == 1


def test_ai_report_created_and_vet_report_blocked(client, farmer, poultry_id):
    pid = upload(client, farmer, poultry_id).json()["prediction_id"]
    reps = client.get(f"/api/reports?prediction_id={pid}", headers=farmer).json()
    assert len(reps) == 1 and reps[0]["report_type"] == "ai"
    c = reps[0]["content"]
    assert c["predicted_disease"] == "Coccidiosis" and "Healthy Probability" in c["probabilities"]
    assert c["veterinary_review_status"] == "Pending Veterinary Review"
    r = client.post("/api/reports", json={"prediction_id": pid, "report_type": "veterinary"}, headers=farmer)
    assert r.status_code == 409
    assert client.get(f"/api/reports/{reps[0]['report_id']}", headers=farmer).status_code == 200


def test_low_confidence(client, farmer, poultry_id):
    from backend.main import app
    from backend.services.model_service import get_predictor
    from tests.conftest import StubPredictor
    app.dependency_overrides[get_predictor] = lambda: StubPredictor((0.30, 0.35, 0.20, 0.15))
    d = upload(client, farmer, poultry_id).json()
    assert d["low_confidence"] is True
    assert "Veterinary assessment is strongly recommended" in d["low_confidence_message"]


def test_invalid_uploads_rejected(client, farmer, poultry_id):
    assert upload(client, farmer, poultry_id, b"hello", "x.jpg").status_code == 400          # unreadable
    assert upload(client, farmer, poultry_id, make_image(), "x.gif").status_code == 400       # extension
    assert upload(client, farmer, poultry_id, b"", "x.jpg").status_code == 400                # empty
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "PNG")
    assert upload(client, farmer, poultry_id, buf.getvalue(), "tiny.png").status_code == 400  # too small
    assert upload(client, farmer, poultry_id, make_image("PNG"), "disguised.jpg").status_code == 201  # real PNG ok
    big = make_image() + b"0" * (6 * 1024 * 1024)
    assert upload(client, farmer, poultry_id, big, "big.jpg").status_code == 201
    assert len(client.get("/api/predictions", headers=farmer).json()) == 2  # 20 MB policy accepts a 6 MB image


def test_filename_never_trusted(client, farmer, poultry_id):
    d = upload(client, farmer, poultry_id, filename="../../etc/passwd.jpg").json()
    from backend.database.session import new_session
    from backend.models.models import PredictionHistory
    db = new_session()
    try:
        fn = db.get(PredictionHistory, d["prediction_id"]).image_filename
    finally:
        db.close()
    assert "/" not in fn and ".." not in fn and "passwd" not in fn


def test_model_unavailable_returns_503(real_model_client):
    c = real_model_client
    from tests.conftest import register_login
    h = register_login(c, "f@x.com")
    pid = c.post("/api/poultry", json={"poultry_type": "Chicken"}, headers=h).json()["poultry_id"]
    r = upload(c, h, pid)
    assert r.status_code == 503 and r.json()["code"] == "model_unavailable"
    assert "Traceback" not in r.text
    assert c.get("/api/predictions", headers=h).json() == []     # nothing fabricated
    assert c.get("/health").json()["model_available"] is False


def test_privacy_between_farmers(client, farmer, poultry_id):
    from tests.conftest import register_login
    other = register_login(client, "other@test.com", "farmer", "Other")
    pid = upload(client, farmer, poultry_id).json()["prediction_id"]
    assert client.get(f"/api/predictions/{pid}", headers=other).status_code == 404
    assert client.get(f"/api/predictions/{pid}/image", headers=other).status_code == 404
    assert client.get(f"/api/poultry/{poultry_id}", headers=other).status_code == 404
    assert client.get(f"/api/reports?prediction_id={pid}", headers=other).status_code == 404
    assert upload(client, other, poultry_id).status_code == 404      # cannot use another farmer's poultry
