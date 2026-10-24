from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import require_roles
from backend.core.config import CLASS_NAMES, settings
from backend.core.exceptions import NotFound
from backend.core.security import hash_password
from backend.database.session import get_db
from backend.models.models import (AuditLog, DiseaseKnowledge, MedicationReference, Notification, Poultry,
                                   PredictionHistory, User)
from backend.schemas.schemas import (AdminUserCreate, AdminUserUpdate, BroadcastIn, DiseaseUpdate,
                                     MedicationIn, UserOut)
from backend.services.audit import audit
from backend.services.model_service import get_predictor
from backend.services.notifications import notify, notify_role
from backend.services.report_service import serialize_prediction

router = APIRouter(prefix="/api/admin", tags=["Administration"])
ADMIN = require_roles("admin")


@router.get("/users", response_model=list[UserOut])
def list_users(role: str | None = None, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    q = select(User).order_by(User.user_id)
    if role:
        q = q.where(User.role == role)
    return list(db.scalars(q))


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: AdminUserCreate, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "An account with this email already exists.")
    u = User(full_name=body.full_name, email=body.email.lower(), role=body.role, contact_number=body.contact_number,
             location=body.location, license_number=body.license_number, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    audit(db, admin.user_id, "admin_user_created", "user", u.user_id, {"role": u.role})
    return u


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: AdminUserUpdate, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise NotFound("User not found.")
    data = body.model_dump(exclude_unset=True)
    if u.user_id == admin.user_id and (data.get("is_active") is False or data.get("role") not in (None, "admin")):
        raise HTTPException(400, "Administrators cannot deactivate or demote themselves.")
    for k, v in data.items():
        if v is not None:
            setattr(u, k, v)
    db.commit()
    audit(db, admin.user_id, "admin_user_updated", "user", u.user_id, data)
    return u


@router.get("/statistics")
def statistics(admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    def cnt(model, *conds):
        return db.scalar(select(func.count()).select_from(model).where(*conds)) or 0
    dist = dict(db.execute(select(PredictionHistory.predicted_class, func.count())
                           .group_by(PredictionHistory.predicted_class)).all())
    return {
        "total_users": cnt(User), "total_farmers": cnt(User, User.role == "farmer"),
        "total_veterinarians": cnt(User, User.role == "veterinarian"),
        "total_poultry": cnt(Poultry), "total_predictions": cnt(PredictionHistory),
        "pending_reviews": cnt(PredictionHistory, PredictionHistory.status.in_(["Pending Review", "Under Review"])),
        "confirmed_diagnoses": cnt(PredictionHistory, PredictionHistory.status.in_(
            ["Diagnosis Confirmed", "Diagnosis Revised", "Treatment Issued", "Follow-up Required", "Completed"])),
        "disease_distribution": {c: int(dist.get(c, 0)) for c in CLASS_NAMES},
        "recent_activity": [{"action": l.action, "entity": l.entity, "entity_id": l.entity_id, "user_id": l.user_id,
                             "timestamp": l.timestamp.isoformat()}
                            for l in db.scalars(select(AuditLog).order_by(AuditLog.log_id.desc()).limit(10))],
    }


@router.get("/logs")
def logs(action: str | None = None, limit: int = 200, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.log_id.desc())
    if action:
        q = q.where(AuditLog.action == action)
    return [{"log_id": l.log_id, "user_id": l.user_id, "action": l.action, "entity": l.entity,
             "entity_id": l.entity_id, "timestamp": l.timestamp.isoformat(), "details": l.details}
            for l in db.scalars(q.limit(min(limit, 1000)))]


@router.get("/predictions")
def all_predictions(limit: int = 200, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    rows = db.scalars(select(PredictionHistory).order_by(PredictionHistory.created_at.desc()).limit(min(limit, 1000)))
    return [serialize_prediction(db, p, include_review=False) for p in rows]


@router.get("/poultry")
def all_poultry(admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    return [{"poultry_id": p.poultry_id, "owner": p.owner.full_name, "type": p.poultry_type, "breed": p.breed,
             "flock_size": p.flock_size, "cases": len(p.predictions)} for p in db.scalars(select(Poultry))]


@router.get("/model", summary="Model information and (real) evaluation results")
def model_info(admin: User = Depends(ADMIN)):
    pred = get_predictor()
    model_available = pred.is_available()
    ev_path = settings().reports_dir / "evaluation_results.json"
    evaluation = json.loads(ev_path.read_text()) if (model_available and ev_path.exists()) else None
    return {
        "model_available": model_available,
        "metadata": pred.metadata(),
        "evaluation": evaluation,
        "evaluation_message": None if evaluation is not None else "Model evaluation results are not yet available.",
        "confidence_threshold": settings().confidence_threshold,
    }


@router.get("/settings")
def system_settings(admin: User = Depends(ADMIN)):
    c = settings()
    return {"confidence_threshold": c.confidence_threshold, "max_upload_mb": c.max_upload_bytes // (1024 * 1024),
            "allowed_extensions": list(c.allowed_extensions), "token_expire_minutes": c.access_token_expire_minutes}


@router.put("/diseases/{disease_id}")
def update_disease(disease_id: int, body: DiseaseUpdate, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    d = db.get(DiseaseKnowledge, disease_id)
    if d is None:
        raise NotFound("Disease not found.")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(d, k, v)
    db.commit()
    audit(db, admin.user_id, "disease_info_updated", "disease_knowledge", disease_id)
    return {"disease_id": d.disease_id, "disease_name": d.disease_name}


@router.post("/medications", status_code=201)
def add_medication(body: MedicationIn, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    if body.disease_class not in CLASS_NAMES:
        raise HTTPException(422, "Unknown disease class.")
    m = MedicationReference(**body.model_dump())
    db.add(m)
    db.commit()
    audit(db, admin.user_id, "medication_reference_created", "medication_reference", m.medication_id)
    return {"medication_id": m.medication_id}


@router.delete("/medications/{medication_id}", status_code=204)
def delete_medication(medication_id: int, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    m = db.get(MedicationReference, medication_id)
    if m is None:
        raise NotFound("Medication reference not found.")
    db.delete(m)
    db.commit()
    audit(db, admin.user_id, "medication_reference_deleted", "medication_reference", medication_id)
    return Response(status_code=204)


@router.post("/notifications/broadcast")
def broadcast(body: BroadcastIn, admin: User = Depends(ADMIN), db: Session = Depends(get_db)):
    if body.role:
        notify_role(db, body.role, body.title, body.message)
    else:
        for uid in db.scalars(select(User.user_id).where(User.is_active.is_(True))):
            notify(db, uid, body.title, body.message)
    audit(db, admin.user_id, "notification_broadcast", "notification", None, {"role": body.role}, commit=False)
    db.commit()
    return {"status": "sent"}
