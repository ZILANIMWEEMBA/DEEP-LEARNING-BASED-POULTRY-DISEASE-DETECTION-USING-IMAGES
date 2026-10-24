from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_prediction_for_user
from backend.core.exceptions import Forbidden
from backend.database.session import get_db
from backend.models.models import Consultation, User
from backend.schemas.schemas import ConsultationIn, ConsultationOut
from backend.services.audit import audit
from backend.services.notifications import notify, notify_role

router = APIRouter(prefix="/api/consultations", tags=["Consultations"])


def _out(c: Consultation) -> ConsultationOut:
    return ConsultationOut(consultation_id=c.consultation_id, prediction_id=c.prediction_id, sender_id=c.sender_id,
                           sender_name=c.sender.full_name, sender_role=c.sender.role, message=c.message,
                           is_request=c.is_request, created_at=c.created_at)


@router.post("", response_model=ConsultationOut, status_code=201,
             summary="Request veterinary consultation / send a message on a case")
def post_message(body: ConsultationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        raise Forbidden("Administrators cannot post consultation messages.")
    p = get_prediction_for_user(db, body.prediction_id, user)
    c = Consultation(prediction_id=p.prediction_id, sender_id=user.user_id, message=body.message.strip(),
                     is_request=bool(body.is_request and user.role == "farmer"))
    db.add(c)
    if user.role == "farmer":
        title = "New consultation request" if c.is_request else "Farmer submitted additional information"
        if p.assigned_vet_id:
            notify(db, p.assigned_vet_id, title, f"{p.case_id}: {body.message[:120]}", p.prediction_id)
        else:
            notify_role(db, "veterinarian", title, f"{p.case_id}: {body.message[:120]}", p.prediction_id)
        if c.is_request:
            notify(db, user.user_id, "Veterinary review requested", f"{p.case_id}: your request was sent.", p.prediction_id)
    else:
        notify(db, p.poultry.user_id, "New message from your veterinarian", f"{p.case_id}: {body.message[:120]}", p.prediction_id)
    audit(db, user.user_id, "consultation_message", "prediction", p.prediction_id, commit=False)
    db.commit()
    return _out(c)


@router.get("", response_model=list[ConsultationOut])
def list_messages(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, prediction_id, user)
    rows = db.scalars(select(Consultation).where(Consultation.prediction_id == p.prediction_id)
                      .order_by(Consultation.created_at)).all()
    return [_out(c) for c in rows]
