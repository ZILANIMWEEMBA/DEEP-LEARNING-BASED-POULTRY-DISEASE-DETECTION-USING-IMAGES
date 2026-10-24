"""End-to-end acceptance test: the complete workflow from the specification."""
from tests.conftest import register_login, upload


def test_poultry_crud(client, farmer):
    r = client.post("/api/poultry", json={"poultry_type": "Chicken", "flock_size": 10}, headers=farmer)
    pid = r.json()["poultry_id"]
    assert client.put(f"/api/poultry/{pid}", json={"flock_size": 20}, headers=farmer).json()["flock_size"] == 20
    assert len(client.get("/api/poultry", headers=farmer).json()) == 1
    assert client.post("/api/poultry", json={"poultry_type": "C", "flock_size": 0}, headers=farmer).status_code == 422
    assert client.delete(f"/api/poultry/{pid}", headers=farmer).status_code == 204


def test_cannot_delete_poultry_with_history(client, farmer, poultry_id):
    upload(client, farmer, poultry_id)
    assert client.delete(f"/api/poultry/{poultry_id}", headers=farmer).status_code == 409


def test_reference_endpoints(client, farmer):
    d = client.get("/api/diseases", headers=farmer).json()
    assert {x["disease_name"] for x in d} == {"Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"}
    meds = client.get("/api/medications?disease_class=Salmonella", headers=farmer).json()
    assert meds and meds[0]["notice"] == "AI Care Suggestion – Not a Prescription"
    assert all("dosage" not in m for m in meds)


def test_full_acceptance_workflow(client, farmer, vet, admin, poultry_id):
    # farmer uploads -> AI prediction -> queue
    case = upload(client, farmer, poultry_id).json()
    pid = case["prediction_id"]

    # veterinarian sees it in the queue and opens it
    q = client.get("/api/veterinary/cases", headers=vet).json()
    assert [c["prediction_id"] for c in q] == [pid] and q[0]["status"] == "Pending Review"
    detail = client.get(f"/api/veterinary/cases/{pid}", headers=vet).json()
    assert detail["case"]["predicted_class"] == "Coccidiosis" and detail["poultry"]["flock_size"] == 50
    assert client.get(detail["case"]["image_url"], headers=vet).status_code == 200
    assert client.post(f"/api/veterinary/cases/{pid}/claim", headers=vet).json()["status"] == "Under Review"

    # farmer cannot use vet endpoints / prescription is vet-only
    body = {"prediction_id": pid, "diagnosis": "Coccidiosis", "diagnosis_action": "confirmed",
            "treatment_plan": "Isolate affected birds", "prescription": "Amprolium", "dosage": "per label",
            "frequency": "daily", "duration": "5 days", "mark_completed": False}
    assert client.post("/api/veterinary/review", json=body, headers=farmer).status_code == 403

    # incomplete prescription rejected
    bad = {**body, "dosage": None}
    assert client.post("/api/veterinary/review", json=bad, headers=vet).status_code == 422
    # confirmed diagnosis must match the AI class
    assert client.post("/api/veterinary/review", json={**body, "diagnosis": "Salmonella"}, headers=vet).status_code == 422

    r = client.post("/api/veterinary/review", json=body, headers=vet)
    assert r.status_code == 201, r.text
    assert r.json()["case"]["status_label"] == "Treatment Approved"
    review_id = r.json()["review"]["review_id"]
    assert client.post("/api/veterinary/review", json=body, headers=vet).status_code == 409   # one review per case

    # farmer sees professional plan + notifications; AI and vet reports are separate
    mine = client.get(f"/api/predictions/{pid}", headers=farmer).json()
    assert mine["review"]["prescription"] == "Amprolium" and mine["review"]["license_info"] == "VET-123"
    assert mine["predicted_class"] == "Coccidiosis"  # AI output unchanged
    titles = [n["title"] for n in client.get("/api/notifications", headers=farmer).json()]
    assert "Treatment plan available" in titles and "Diagnosis confirmed" in titles
    types = {r["report_type"] for r in client.get(f"/api/reports?prediction_id={pid}", headers=farmer).json()}
    assert types == {"ai", "veterinary"}
    vr = client.post("/api/reports", json={"prediction_id": pid, "report_type": "veterinary"}, headers=farmer).json()
    assert vr["content"]["confirmed_diagnosis"] == "Coccidiosis" and vr["content"]["professional_credentials"] == "VET-123"
    n = client.get("/api/notifications", headers=farmer).json()[0]
    assert client.put(f"/api/notifications/{n['notification_id']}/read", headers=farmer).json()["is_read"] is True

    # revision by the same vet is audited; another vet cannot edit
    other_vet = register_login(client, "vet2@test.com", "veterinarian", "Dr Two", license_number="V2")
    assert client.put(f"/api/veterinary/review/{review_id}", json={"veterinary_comments": "x"}, headers=other_vet).status_code in (403,)
    r = client.put(f"/api/veterinary/review/{review_id}",
                   json={"diagnosis": "Salmonella", "diagnosis_action": "revised", "prescription": None,
                         "dosage": None, "frequency": None, "duration": None}, headers=vet)
    assert r.status_code == 200 and r.json()["case"]["status_label"] == "Veterinarian Revised"

    # consultation messages
    assert client.post("/api/consultations", json={"prediction_id": pid, "message": "Birds still sick", "is_request": True},
                       headers=farmer).status_code == 201
    assert len(client.get(f"/api/consultations?prediction_id={pid}", headers=vet).json()) == 1

    # audit trail
    actions = {l["action"] for l in client.get("/api/admin/logs?limit=500", headers=admin).json()}
    assert {"login", "image_upload", "prediction_created", "report_created", "veterinary_review",
            "prescription_created", "diagnosis_change", "case_claimed"} <= actions
    stats = client.get("/api/admin/statistics", headers=admin).json()
    assert stats["total_predictions"] == 1 and stats["total_farmers"] == 1 and stats["total_veterinarians"] == 2
    assert stats["disease_distribution"]["Coccidiosis"] == 1


def test_case_assigned_to_other_vet_is_hidden(client, farmer, vet, poultry_id):
    pid = upload(client, farmer, poultry_id).json()["prediction_id"]
    client.post(f"/api/veterinary/cases/{pid}/claim", headers=vet)
    other = register_login(client, "vet2@test.com", "veterinarian", "Dr Two", license_number="V2")
    assert client.get(f"/api/veterinary/cases/{pid}", headers=other).status_code == 403
    assert client.get("/api/veterinary/cases", headers=other).json() == []


def test_vet_status_update_and_stats(client, farmer, vet, poultry_id):
    pid = upload(client, farmer, poultry_id).json()["prediction_id"]
    assert client.get("/api/veterinary/stats", headers=vet).json()["pending"] == 1
    r = client.put(f"/api/veterinary/cases/{pid}/status",
                   json={"status": "Rejected / Insufficient Information", "comment": "Blurry image"}, headers=vet)
    assert r.json()["status"] == "Rejected / Insufficient Information"


def test_openapi_docs(client):
    assert client.get("/docs").status_code == 200 and client.get("/redoc").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/api/predictions" in spec["paths"] and "/api/veterinary/review" in spec["paths"]


def test_admin_model_info_not_fabricated(client, admin):
    m = client.get("/api/admin/model", headers=admin).json()
    assert m["evaluation"] is None and m["evaluation_message"] == "Model evaluation results are not yet available."


def test_invalid_request_clean_error(client, farmer):
    r = client.post("/api/poultry", json={"age": "abc"}, headers=farmer)
    assert r.status_code == 422 and r.json()["code"] == "invalid_request" and "Traceback" not in r.text
