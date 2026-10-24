from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_poultry_for_user, get_prediction_for_user, require_roles
from backend.core.config import settings
from backend.core.exceptions import ImageTooLarge, NotFound
from backend.database.session import get_db
from backend.models.models import Poultry, PredictionHistory, User
from backend.services.image_service import image_path
from backend.services.model_service import get_predictor
from backend.services.prediction_service import create_prediction
from backend.services.report_service import serialize_prediction
from machine_learning.inference.predictor import PoultryPredictor

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.post("", status_code=201, summary="Upload an image and obtain an AI decision-support prediction")
async def predict(poultry_id: int = Form(...), file: UploadFile = File(...),
                  symptoms: str | None = Form(None), observations: str | None = Form(None),
                  user: User = Depends(require_roles("farmer")), db: Session = Depends(get_db),
                  predictor: PoultryPredictor = Depends(get_predictor)):
    poultry = get_poultry_for_user(db, poultry_id, user, write=True)
    cap = settings().max_upload_bytes
    data = await file.read(cap + 1)  # never read unbounded input
    if len(data) > cap:
        raise ImageTooLarge(f"Image is too large. Maximum size is {cap // (1024 * 1024)} MB.")
    pred = create_prediction(db, user, poultry, data, file.filename,
                             (symptoms or "").strip()[:2000] or None,
                             (observations or "").strip()[:2000] or None, predictor)
    return serialize_prediction(db, pred)


def _visible_query(user: User):
    q = select(PredictionHistory).order_by(PredictionHistory.created_at.desc())
    if user.role == "farmer":
        q = q.join(Poultry).where(Poultry.user_id == user.user_id)
    elif user.role == "veterinarian":
        q = q.where((PredictionHistory.assigned_vet_id.is_(None)) | (PredictionHistory.assigned_vet_id == user.user_id))
    return q


@router.get("", summary="Prediction history visible to the caller")
def list_predictions(poultry_id: int | None = None, status: str | None = None, limit: int = 100,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = _visible_query(user)
    if poultry_id:
        q = q.where(PredictionHistory.poultry_id == poultry_id)
    if status:
        q = q.where(PredictionHistory.status == status)
    rows = db.scalars(q.limit(min(max(limit, 1), 500))).all()
    return [serialize_prediction(db, p) for p in rows]


@router.get("/summary/me", summary="Dashboard counters for the farmer")
def my_summary(user: User = Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    base = select(func.count()).select_from(PredictionHistory).join(Poultry).where(Poultry.user_id == user.user_id)
    pending = base.where(PredictionHistory.status.in_(["Pending Review", "Under Review"]))
    confirmed = base.where(PredictionHistory.status.in_(
        ["Diagnosis Confirmed", "Diagnosis Revised", "Treatment Issued", "Follow-up Required", "Completed"]))
    return {
        "registered_poultry": db.scalar(select(func.count()).select_from(Poultry).where(Poultry.user_id == user.user_id)),
        "total_predictions": db.scalar(base), "pending_reviews": db.scalar(pending),
        "confirmed_diagnoses": db.scalar(confirmed),
    }


@router.get("/{prediction_id}")
def get_prediction(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_prediction(db, get_prediction_for_user(db, prediction_id, user))


@router.get("/{prediction_id}/image", summary="Access-controlled image download")
def get_image(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pred = get_prediction_for_user(db, prediction_id, user)
    path = image_path(pred.image_filename)
    if not path.exists():
        raise NotFound("Image file is no longer available.")
    return FileResponse(path, headers={"Cache-Control": "private, no-store"})
