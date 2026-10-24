from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_poultry_for_user, get_prediction_for_user, require_roles
from backend.core.exceptions import Conflict, Forbidden, NotFound
from backend.database.session import get_db
from backend.models.models import Consultation, Poultry, PredictionHistory, Report, User, VeterinaryReview, utcnow
from backend.schemas.schemas import CaseStatusIn, ReviewIn, ReviewUpdate
from backend.services.audit import audit
from backend.services.notifications import notify
from backend.services.report_service import (build_ai_report, review_dict, save_report,
                                             serialize_prediction, poultry_code)

router = APIRouter(prefix="/api/veterinary", tags=["Veterinary workflow"])
VET = require_roles("veterinarian")


def _case_row(db: Session, p: PredictionHistory) -> dict:
    return {"prediction_id": p.prediction_id, "case_id": p.case_id,
            "farmer": p.poultry.owner.full_name, "poultry_id": poultry_code(p.poultry_id),
            "ai_prediction": p.predicted_class, "confidence": p.confidence,
            "low_confidence": p.low_confidence, "date": p.created_at.isoformat(),
            "status": p.status, "assigned_vet_id": p.assigned_vet_id}


@router.get("/cases", summary="Veterinary case queue (unassigned + assigned to me)")
def cases(status: str | None = None, mine: bool = False, user: User = Depends(VET), db: Session = Depends(get_db)):
    q = select(PredictionHistory).order_by(PredictionHistory.created_at.desc())
    if mine:
        q = q.where(PredictionHistory.assigned_vet_id == user.user_id)
    else:
        q = q.where(PredictionHistory.assigned_vet_id.is_(None) | (PredictionHistory.assigned_vet_id == user.user_id))
    if status:
        q = q.where(PredictionHistory.status == status)
    return [_case_row(db, p) for p in db.scalars(q.limit(500))]


@router.get("/stats")
def stats(user: User = Depends(VET), db: Session = Depends(get_db)):
    def count(*statuses: str, mine_only: bool = False) -> int:
        q = select(func.count()).select_from(PredictionHistory).where(PredictionHistory.status.in_(statuses))
        if mine_only:
            q = q.where(PredictionHistory.assigned_vet_id == user.user_id)
        else:
            q = q.where(PredictionHistory.assigned_vet_id.is_(None) | (PredictionHistory.assigned_vet_id == user.user_id))
        return db.scalar(q) or 0
    return {"pending": count("Pending Review"), "under_review": count("Under Review", mine_only=True),
            "confirmed": count("Diagnosis Confirmed", "Treatment Issued", "Completed", mine_only=True),
            "revised": count("Diagnosis Revised", mine_only=True),
            "follow_up": count("Follow-up Required", mine_only=True)}


@router.get("/cases/{prediction_id}", summary="Full case detail for review")
def case_detail(prediction_id: int, user: User = Depends(VET), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, prediction_id, user)
    owner = p.poultry.owner
    history = db.scalars(select(PredictionHistory).where(PredictionHistory.poultry_id == p.poultry_id)
                         .order_by(PredictionHistory.created_at.desc())).all()
    msgs = db.scalars(select(Consultation).where(Consultation.prediction_id == p.prediction_id)
                      .order_by(Consultation.created_at)).all()
    return {
        "case": serialize_prediction(db, p),
        "ai_report": build_ai_report(db, p),
        "farmer": {"name": owner.full_name, "contact_number": owner.contact_number, "location": owner.location},
        "poultry": {"poultry_id": poultry_code(p.poultry_id), "type": p.poultry.poultry_type, "breed": p.poultry.breed,
                    "age_weeks": p.poultry.age, "flock_size": p.poultry.flock_size,
                    "production_type": p.poultry.production_type, "health_history": p.poultry.health_history},
        "poultry_history": [{"case_id": h.case_id, "predicted_class": h.predicted_class, "status": h.status,
                             "date": h.created_at.isoformat()} for h in history],
        "consultations": [{"sender": m.sender.full_name, "role": m.sender.role, "message": m.message,
                           "is_request": m.is_request, "created_at": m.created_at.isoformat()} for m in msgs],
    }


@router.post("/cases/{prediction_id}/claim", summary="Open a case: assign to me and set Under Review")
def claim(prediction_id: int, user: User = Depends(VET), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, prediction_id, user)
    if p.assigned_vet_id is None:
        p.assigned_vet_id = user.user_id
        if p.status == "Pending Review":
            p.status = "Under Review"
        notify(db, p.poultry.user_id, "Veterinarian reviewing your case",
               f"{p.case_id} is now under review by {user.full_name}.", p.prediction_id)
        audit(db, user.user_id, "case_claimed", "prediction", p.prediction_id, commit=False)
        db.commit()
    return serialize_prediction(db, p)


@router.put("/cases/{prediction_id}/status")
def set_status(prediction_id: int, body: CaseStatusIn, user: User = Depends(VET), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, prediction_id, user)
    if p.assigned_vet_id is None:
        p.assigned_vet_id = user.user_id
    old, p.status = p.status, body.status
    notify(db, p.poultry.user_id, f"Case status: {body.status}",
           f"{p.case_id}: {body.comment or 'Status updated by your veterinarian.'}", p.prediction_id)
    audit(db, user.user_id, "case_status_changed", "prediction", p.prediction_id,
          {"from": old, "to": body.status, "comment": body.comment}, commit=False)
    db.commit()
    return serialize_prediction(db, p)


def _status_after_review(action: str, has_rx: bool, follow_up: bool, completed: bool) -> str:
    if completed:
        return "Completed"
    if follow_up:
        return "Follow-up Required"
    if has_rx:
        return "Treatment Issued"
    return "Diagnosis Revised" if action == "revised" else "Diagnosis Confirmed"


@router.post("/review", status_code=201, summary="Confirm/revise diagnosis and issue treatment (veterinarian only)")
def create_review(body: ReviewIn, user: User = Depends(VET), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, body.prediction_id, user)
    if p.review is not None:
        raise Conflict("This case already has a veterinary review. Use PUT /api/veterinary/review/{id}.")
    if body.diagnosis_action == "confirmed" and body.diagnosis.strip().lower() != p.predicted_class.lower():
        raise HTTPException(422, "A 'confirmed' diagnosis must match the AI prediction; choose 'revised' to change it.")
    if body.diagnosis_action == "revised" and body.diagnosis.strip().lower() == p.predicted_class.lower():
        raise HTTPException(422, "A 'revised' diagnosis must differ from the AI prediction.")
    has_rx = bool((body.prescription or "").strip())
    rev = VeterinaryReview(
        prediction_id=p.prediction_id, vet_id=user.user_id, diagnosis=body.diagnosis.strip(),
        diagnosis_action=body.diagnosis_action, clinical_assessment=body.clinical_assessment,
        treatment_plan=body.treatment_plan, prescription=(body.prescription or None), dosage=body.dosage,
        frequency=body.frequency, duration=body.duration, additional_instructions=body.additional_instructions,
        follow_up_date=body.follow_up_date, license_info=user.license_number,
        veterinary_comments=body.veterinary_comments)
    db.add(rev)
    p.review = rev
    rev.veterinarian = user
    p.assigned_vet_id = user.user_id
    p.status = _status_after_review(body.diagnosis_action, has_rx, body.follow_up_date is not None, body.mark_completed)
    db.flush()
    save_report(db, p, "veterinary", user.user_id)
    uid = p.poultry.user_id
    notify(db, uid, "Veterinarian reviewed your case", f"{p.case_id}: reviewed by {user.full_name}.", p.prediction_id)
    notify(db, uid, "Diagnosis revised" if body.diagnosis_action == "revised" else "Diagnosis confirmed",
           f"{p.case_id}: veterinary diagnosis is {rev.diagnosis}.", p.prediction_id)
    if has_rx or body.treatment_plan:
        notify(db, uid, "Treatment plan available", f"{p.case_id}: your veterinarian issued a treatment plan.", p.prediction_id)
    if body.follow_up_date:
        notify(db, uid, "Follow-up required", f"{p.case_id}: follow-up on {body.follow_up_date:%Y-%m-%d}.", p.prediction_id)
    audit(db, user.user_id, "veterinary_review", "prediction", p.prediction_id,
          {"action": body.diagnosis_action, "diagnosis": rev.diagnosis}, commit=False)
    if body.diagnosis_action == "revised":
        audit(db, user.user_id, "diagnosis_change", "prediction", p.prediction_id,
              {"ai": p.predicted_class, "vet": rev.diagnosis}, commit=False)
    if has_rx:
        audit(db, user.user_id, "prescription_created", "veterinary_review", rev.review_id,
              {"medication": rev.prescription}, commit=False)
    audit(db, user.user_id, "report_created", "report", p.prediction_id, {"type": "veterinary"}, commit=False)
    db.commit()
    return {"review": review_dict(rev, user), "case": serialize_prediction(db, p)}


@router.put("/review/{review_id}", summary="Update an existing review (owning veterinarian only)")
def update_review(review_id: int, body: ReviewUpdate, user: User = Depends(VET), db: Session = Depends(get_db)):
    rev = db.get(VeterinaryReview, review_id)
    if rev is None:
        raise NotFound("Veterinary review not found.")
    if rev.vet_id != user.user_id:
        raise Forbidden("Only the reviewing veterinarian can modify this review.")
    p = rev.prediction
    data = body.model_dump(exclude_unset=True)
    old_dx, old_rx = rev.diagnosis, rev.prescription
    completed = data.pop("mark_completed", None)
    for k, v in data.items():
        setattr(rev, k, v)
    if rev.prescription and rev.prescription.strip():
        missing = [n for n in ("dosage", "frequency", "duration") if not (getattr(rev, n) or "").strip()]
        if missing:
            db.rollback()
            raise HTTPException(422, f"A prescription requires: {', '.join(missing)}.")
    if rev.diagnosis_action == "confirmed" and rev.diagnosis.strip().lower() != p.predicted_class.lower():
        db.rollback()
        raise HTTPException(422, "A 'confirmed' diagnosis must match the AI prediction; use 'revised'.")
    rev.reviewed_at = utcnow()
    p.status = _status_after_review(rev.diagnosis_action, bool(rev.prescription), rev.follow_up_date is not None,
                                    bool(completed))
    db.flush()
    save_report(db, p, "veterinary", user.user_id)
    notify(db, p.poultry.user_id, "Veterinary review updated", f"{p.case_id}: your veterinarian updated the plan.", p.prediction_id)
    if rev.diagnosis != old_dx:
        audit(db, user.user_id, "diagnosis_change", "veterinary_review", rev.review_id,
              {"from": old_dx, "to": rev.diagnosis}, commit=False)
    if rev.prescription != old_rx:
        audit(db, user.user_id, "prescription_updated", "veterinary_review", rev.review_id, commit=False)
    audit(db, user.user_id, "veterinary_review_updated", "veterinary_review", rev.review_id, commit=False)
    db.commit()
    return {"review": review_dict(rev, user), "case": serialize_prediction(db, p)}


@router.get("/poultry/{poultry_id}/history")
def poultry_history(poultry_id: int, user: User = Depends(VET), db: Session = Depends(get_db)):
    pt = get_poultry_for_user(db, poultry_id, user)
    return [serialize_prediction(db, p) for p in sorted(pt.predictions, key=lambda x: x.created_at, reverse=True)
            if p.assigned_vet_id in (None, user.user_id)]
