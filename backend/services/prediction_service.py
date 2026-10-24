"""Orchestrates: validate image -> predict -> persist -> AI report -> queue -> notify."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.exceptions import ModelUnavailableError, PredictionFailure
from backend.core.logging_config import get_logger
from backend.models.models import Poultry, PredictionHistory, UploadedImage, User
from backend.services.audit import audit
from backend.services.image_service import store_image, validate_image
from backend.services.notifications import notify, notify_role
from backend.services.report_service import save_report
from machine_learning.inference.predictor import PoultryPredictor

log = get_logger("prediction")


def create_prediction(db: Session, user: User, poultry: Poultry, data: bytes, filename: str | None,
                      symptoms: str | None, observations: str | None,
                      predictor: PoultryPredictor) -> PredictionHistory:
    cfg = settings()
    # 1. validate BEFORE the model ever sees the file
    ext, w, h = validate_image(data, filename)
    audit(db, user.user_id, "prediction_requested", "poultry", poultry.poultry_id)

    # 2. inference (raises ModelUnavailableError / PredictionFailure - nothing is fabricated)
    try:
        result = predictor.predict(data)
    except (ModelUnavailableError, PredictionFailure) as exc:
        audit(db, user.user_id, "prediction_failed", "poultry", poultry.poultry_id, {"error": exc.code})
        raise

    # 3. store image only after successful validation + prediction
    stored, sha = store_image(data, ext)
    img = UploadedImage(stored_filename=stored, original_extension=ext, size_bytes=len(data),
                        width=w, height=h, sha256=sha, uploaded_by=user.user_id)
    db.add(img)
    db.flush()
    audit(db, user.user_id, "image_upload", "uploaded_image", img.image_id, commit=False)

    probs = result["probabilities"]
    pred = PredictionHistory(
        poultry_id=poultry.poultry_id, image_id=img.image_id, image_filename=stored,
        predicted_class=result["predicted_class"], confidence=result["confidence"],
        healthy_prob=probs["Healthy"], coccidiosis_prob=probs["Coccidiosis"],
        newcastle_prob=probs["Newcastle Disease"], salmonella_prob=probs["Salmonella"],
        low_confidence=result["confidence"] < cfg.confidence_threshold,
        symptoms=(symptoms or None), farmer_observations=(observations or None),
        status="Pending Review", model_version=predictor.version)
    db.add(pred)
    db.flush()

    # 4. AI report + veterinary queue + notifications
    save_report(db, pred, "ai", user.user_id)
    notify(db, user.user_id, "Prediction completed",
           f"{pred.case_id}: AI prediction is ready and waiting for veterinary review.", pred.prediction_id)
    notify_role(db, "veterinarian", "New case assigned to queue",
                f"{pred.case_id} ({pred.predicted_class}, {pred.confidence:.0%}) awaits review.", pred.prediction_id)
    audit(db, user.user_id, "prediction_created", "prediction", pred.prediction_id,
          {"class": pred.predicted_class, "confidence": round(pred.confidence, 4)}, commit=False)
    audit(db, user.user_id, "report_created", "report", pred.prediction_id, {"type": "ai"}, commit=False)
    db.commit()
    return pred
