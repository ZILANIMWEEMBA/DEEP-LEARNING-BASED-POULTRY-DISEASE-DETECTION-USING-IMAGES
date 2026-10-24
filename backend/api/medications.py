from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.database.session import get_db
from backend.models.models import DiseaseKnowledge, MedicationReference, User
from backend.services.report_service import disease_info, medication_refs

router = APIRouter(prefix="/api", tags=["Reference information"])


@router.get("/medications", summary="Medication REFERENCE categories (no dosage - not a prescription)")
def medications(disease_class: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(MedicationReference)
    if disease_class:
        q = q.where(MedicationReference.disease_class == disease_class)
    return [{"medication_id": m.medication_id, "disease_class": m.disease_class, "medicine_name": m.medicine_name,
             "category": m.category, "usage_notes": m.usage_notes,
             "notice": "AI Care Suggestion – Not a Prescription"} for m in db.scalars(q)]


@router.get("/diseases", summary="Disease knowledge base")
def diseases(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    names = db.scalars(select(DiseaseKnowledge.disease_name)).all()
    return [{**disease_info(db, n), "medication_reference": medication_refs(db, n)} for n in names]
