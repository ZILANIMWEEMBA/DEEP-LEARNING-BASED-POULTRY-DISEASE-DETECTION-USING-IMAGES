from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_prediction_for_user
from backend.core.exceptions import NotFound
from backend.database.session import get_db
from backend.models.models import Report, User
from backend.schemas.schemas import ReportCreate
from backend.services.audit import audit
from backend.services.report_service import report_out, save_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post("", status_code=201, summary="Generate a report (AI and veterinary reports are separate)")
def create_report(body: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, body.prediction_id, user)
    if body.report_type == "veterinary" and p.review is None:
        raise HTTPException(409, "A veterinary report is only available after a veterinarian has reviewed the case.")
    rep = save_report(db, p, body.report_type, user.user_id)
    audit(db, user.user_id, "report_created", "report", rep.report_id, {"type": body.report_type}, commit=False)
    db.commit()
    return report_out(rep)


@router.get("", summary="List reports for a case")
def list_reports(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_prediction_for_user(db, prediction_id, user)
    rows = db.scalars(select(Report).where(Report.prediction_id == p.prediction_id).order_by(Report.created_at.desc())).all()
    return [report_out(r) for r in rows]


@router.get("/{report_id}")
def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rep = db.get(Report, report_id)
    if rep is None:
        raise NotFound("Report not found.")
    get_prediction_for_user(db, rep.prediction_id, user)  # access control
    return report_out(rep)
