"""Knowledge-base lookups, care suggestion, serialisation and report generation.

AI output and veterinary output are always kept in separate sections/reports.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import (AI_DISCLAIMER_TEXT, AI_DISCLAIMER_TITLE, CONFIDENCE_NOTE,
                                 LOW_CONFIDENCE_MESSAGE, CLASS_NAMES)
from backend.models.models import (DiseaseKnowledge, MedicationReference, PredictionHistory,
                                   Report, User, VeterinaryReview)

STATUS_LABELS = {
    "Pending Review": "Pending Veterinary Review",
    "Under Review": "Under Veterinary Review",
    "Diagnosis Confirmed": "Veterinarian Confirmed",
    "Diagnosis Revised": "Veterinarian Revised",
    "Treatment Issued": "Treatment Approved",
    "Follow-up Required": "Follow-up Required",
    "Completed": "Completed",
    "Rejected / Insufficient Information": "Rejected / Insufficient Information",
}


def poultry_code(poultry_id: int) -> str:
    return f"POULTRY-{poultry_id:05d}"


def disease_info(db: Session, name: str) -> dict:
    d = db.scalar(select(DiseaseKnowledge).where(DiseaseKnowledge.disease_name == name))
    if d is None:
        return {"disease_name": name, "category": "Unknown", "description": "No reference information available.",
                "reference_symptoms": [], "general_care": "", "referral_guidance": "Consult a veterinarian."}
    return {"disease_name": d.disease_name, "category": d.category, "description": d.description,
            "reference_symptoms": [s for s in d.reference_symptoms.split("\n") if s],
            "general_care": d.general_care, "referral_guidance": d.referral_guidance}


def medication_refs(db: Session, name: str) -> list[dict]:
    rows = db.scalars(select(MedicationReference).where(MedicationReference.disease_class == name)).all()
    return [{"medicine_name": r.medicine_name, "category": r.category, "usage_notes": r.usage_notes} for r in rows]


def care_suggestion(info: dict, low_confidence: bool) -> str:
    text = f"{info['general_care']} {info['referral_guidance']}".strip()
    if low_confidence:
        text = f"{LOW_CONFIDENCE_MESSAGE} {text}"
    return text


def prediction_probs(p: PredictionHistory) -> dict[str, float]:
    vals = [p.healthy_prob, p.coccidiosis_prob, p.newcastle_prob, p.salmonella_prob]
    return dict(zip(CLASS_NAMES, vals))


def review_dict(r: VeterinaryReview | None, vet: User | None = None) -> dict | None:
    if r is None:
        return None
    vet = vet or r.veterinarian
    return {
        "review_id": r.review_id, "vet_id": r.vet_id, "veterinarian_name": vet.full_name if vet else None,
        "license_info": r.license_info, "diagnosis": r.diagnosis, "diagnosis_action": r.diagnosis_action,
        "clinical_assessment": r.clinical_assessment, "treatment_plan": r.treatment_plan,
        "prescription": r.prescription, "dosage": r.dosage, "frequency": r.frequency, "duration": r.duration,
        "additional_instructions": r.additional_instructions,
        "follow_up_date": r.follow_up_date.isoformat() if r.follow_up_date else None,
        "veterinary_comments": r.veterinary_comments, "reviewed_at": r.reviewed_at.isoformat(),
    }


def serialize_prediction(db: Session, p: PredictionHistory, include_review: bool = True) -> dict:
    info = disease_info(db, p.predicted_class)
    out = {
        "prediction_id": p.prediction_id, "case_id": p.case_id,
        "poultry_id": p.poultry_id, "poultry_code": poultry_code(p.poultry_id),
        "label": "AI Prediction",
        "predicted_class": p.predicted_class, "confidence": p.confidence,
        "probabilities": prediction_probs(p),
        "low_confidence": p.low_confidence,
        "low_confidence_message": LOW_CONFIDENCE_MESSAGE if p.low_confidence else None,
        "confidence_note": CONFIDENCE_NOTE,
        "disease": info,
        "care_suggestion": care_suggestion(info, p.low_confidence),
        "care_suggestion_title": AI_DISCLAIMER_TITLE,
        "disclaimer": AI_DISCLAIMER_TEXT,
        "symptoms": p.symptoms, "farmer_observations": p.farmer_observations,
        "status": p.status, "status_label": STATUS_LABELS.get(p.status, p.status),
        "assigned_vet_id": p.assigned_vet_id,
        "image_url": f"/api/predictions/{p.prediction_id}/image",
        "model_version": p.model_version,
        "created_at": p.created_at.isoformat(),
    }
    if include_review:
        out["review"] = review_dict(p.review)
    return out


# --------------------------------------------------------------- reports
def build_ai_report(db: Session, p: PredictionHistory) -> dict:
    info = disease_info(db, p.predicted_class)
    probs = prediction_probs(p)
    return {
        "report_type": "ai",
        "title": "AI Decision-Support Report (not a veterinary report)",
        "case_id": p.case_id, "poultry_id": poultry_code(p.poultry_id),
        "predicted_disease": p.predicted_class, "confidence": p.confidence,
        "probabilities": {f"{k} Probability": v for k, v in probs.items()},
        "disease_category": info["category"], "description": info["description"],
        "reference_symptoms": info["reference_symptoms"],
        "ai_care_suggestion": care_suggestion(info, p.low_confidence),
        "medication_reference_categories": medication_refs(db, p.predicted_class),
        "low_confidence_warning": LOW_CONFIDENCE_MESSAGE if p.low_confidence else None,
        "timestamp": p.created_at.isoformat(),
        "veterinary_review_status": STATUS_LABELS.get(p.status, p.status),
        "disclaimer_title": AI_DISCLAIMER_TITLE, "disclaimer": AI_DISCLAIMER_TEXT,
        "confidence_note": CONFIDENCE_NOTE,
    }


def build_vet_report(db: Session, p: PredictionHistory) -> dict:
    r = p.review
    if r is None:
        raise ValueError("No veterinary review exists for this case yet.")
    farmer = p.poultry.owner
    return {
        "report_type": "veterinary",
        "title": "Veterinary Report",
        "case_id": p.case_id,
        "farmer": farmer.full_name,
        "poultry": {"poultry_id": poultry_code(p.poultry_id), "type": p.poultry.poultry_type,
                    "breed": p.poultry.breed, "age_weeks": p.poultry.age, "flock_size": p.poultry.flock_size},
        "image": f"/api/predictions/{p.prediction_id}/image",
        "ai_prediction_reference": {"predicted_class": p.predicted_class, "confidence": p.confidence,
                                    "note": "AI prediction shown for reference only; it is not a diagnosis."},
        "veterinarian_assessment": r.clinical_assessment,
        "confirmed_diagnosis": r.diagnosis, "diagnosis_action": r.diagnosis_action,
        "treatment": r.treatment_plan, "prescription": r.prescription, "dosage": r.dosage,
        "frequency": r.frequency, "duration": r.duration,
        "additional_instructions": r.additional_instructions,
        "follow_up": r.follow_up_date.isoformat() if r.follow_up_date else None,
        "veterinarian": r.veterinarian.full_name, "professional_credentials": r.license_info,
        "veterinarian_comments": r.veterinary_comments,
        "date": r.reviewed_at.isoformat(),
    }


def save_report(db: Session, p: PredictionHistory, report_type: str, user_id: int | None) -> Report:
    content = build_ai_report(db, p) if report_type == "ai" else build_vet_report(db, p)
    rep = Report(prediction_id=p.prediction_id, report_type=report_type,
                 content_json=json.dumps(content, default=str), created_by=user_id)
    db.add(rep)
    db.flush()
    return rep


def report_out(rep: Report) -> dict:
    return {"report_id": rep.report_id, "prediction_id": rep.prediction_id, "report_type": rep.report_type,
            "created_at": rep.created_at.isoformat(), "content": json.loads(rep.content_json)}


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
