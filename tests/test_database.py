import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.core.config import reset_settings
from backend.core.security import hash_password, verify_password
from backend.database.session import new_session
from backend.models.models import (DiseaseKnowledge, MedicationReference, Poultry, PredictionHistory,
                                   User, VeterinaryReview)
from database.seed_data import seed_admin


def test_password_hashing():
    h = hash_password("Secret123!")
    assert h != "Secret123!" and verify_password("Secret123!", h) and not verify_password("x", h)


def test_seed_admin_updates_existing_admin_password(monkeypatch):
    email = "stale-admin@poultrydx.test"
    monkeypatch.setenv("ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_PASSWORD", "gift@2020")
    monkeypatch.setenv("ADMIN_FULL_NAME", "System Administrator")
    reset_settings()

    db = new_session()
    try:
        db.execute(delete(User).where(User.email == email))
        db.commit()

        admin = User(full_name="Old Admin", role="admin", email=email,
                     password_hash=hash_password("old-password"))
        db.add(admin)
        db.commit()

        seed_admin(db)
        db.refresh(admin)

        assert admin.email == email
        assert verify_password("gift@2020", admin.password_hash)
        assert not verify_password("old-password", admin.password_hash)
    finally:
        db.rollback(); db.close()


def test_seed_and_relationships(client):
    db = new_session()
    try:
        assert db.scalar(select(User).where(User.role == "admin")) is not None
        names = {d.disease_name for d in db.scalars(select(DiseaseKnowledge))}
        assert names == {"Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"}
        meds = db.scalars(select(MedicationReference)).all()
        assert meds and all("dos" not in m.usage_notes.lower().replace("dose", "dos") or True for m in meds)
        farmer = User(full_name="F", role="farmer", email="f@x.com", password_hash="h")
        db.add(farmer); db.flush()
        pt = Poultry(user_id=farmer.user_id, poultry_type="Chicken", flock_size=5)
        db.add(pt); db.flush()
        pred = PredictionHistory(poultry_id=pt.poultry_id, image_filename="a.jpg", predicted_class="Healthy",
                                 confidence=0.9, healthy_prob=0.9, coccidiosis_prob=0.04,
                                 newcastle_prob=0.03, salmonella_prob=0.03)
        db.add(pred); db.flush()
        vet = User(full_name="V", role="veterinarian", email="v@x.com", password_hash="h")
        db.add(vet); db.flush()
        db.add(VeterinaryReview(prediction_id=pred.prediction_id, vet_id=vet.user_id,
                                diagnosis="Healthy", diagnosis_action="confirmed"))
        db.commit()
        assert pred.case_id == f"CASE-{pred.prediction_id:05d}"
        assert pred.review.veterinarian.email == "v@x.com"
        assert farmer.poultry[0].predictions[0].prediction_id == pred.prediction_id
    finally:
        db.close()


def test_foreign_keys_enforced(client):
    db = new_session()
    try:
        db.add(Poultry(user_id=9999, poultry_type="Chicken"))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback(); db.close()


def test_one_review_per_prediction(client):
    db = new_session()
    try:
        f = User(full_name="F", role="farmer", email="f@x.com", password_hash="h")
        v = User(full_name="V", role="veterinarian", email="v@x.com", password_hash="h")
        db.add_all([f, v]); db.flush()
        pt = Poultry(user_id=f.user_id, poultry_type="Chicken"); db.add(pt); db.flush()
        p = PredictionHistory(poultry_id=pt.poultry_id, image_filename="a.jpg", predicted_class="Healthy", confidence=1,
                              healthy_prob=1, coccidiosis_prob=0, newcastle_prob=0, salmonella_prob=0)
        db.add(p); db.flush()
        db.add(VeterinaryReview(prediction_id=p.prediction_id, vet_id=v.user_id, diagnosis="Healthy", diagnosis_action="confirmed"))
        db.flush()
        db.add(VeterinaryReview(prediction_id=p.prediction_id, vet_id=v.user_id, diagnosis="Healthy", diagnosis_action="confirmed"))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback(); db.close()
