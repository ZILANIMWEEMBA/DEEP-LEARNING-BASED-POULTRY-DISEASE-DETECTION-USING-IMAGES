"""Seed the disease knowledge base, medication REFERENCE info and the first admin.

Medication reference rows contain general categories only - never dosage,
frequency or duration. Those can only be entered by a veterinarian.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.logging_config import get_logger  # noqa: E402
from backend.core.security import hash_password  # noqa: E402
from backend.database.session import init_db, new_session  # noqa: E402
from backend.models.models import DiseaseKnowledge, MedicationReference, User  # noqa: E402

log = get_logger("seed")

DISEASES = [
    dict(
        disease_name="Healthy", category="Normal",
        description="No visible signs of the three target diseases were detected in the image by the model.",
        reference_symptoms="Bright eyes\nAlert behaviour\nClean, intact plumage\nNormal droppings\nNormal feed and water intake",
        general_care="No medication is indicated by the AI prediction. Continue routine hygiene, clean water, balanced nutrition and regular flock observation.",
        referral_guidance="If the bird or flock still looks unwell, consult a veterinarian even if the AI result is Healthy.",
    ),
    dict(
        disease_name="Coccidiosis", category="Parasitic",
        description="A parasitic intestinal disease caused by Eimeria protozoa, common in poultry kept in damp or crowded conditions.",
        reference_symptoms="Bloody or watery droppings\nRuffled feathers and huddling\nReduced appetite\nWeight loss or poor growth\nPale comb and wattles",
        general_care="Keep litter dry, avoid overcrowding, separate visibly sick birds and keep feeders and drinkers clean.",
        referral_guidance="An anticoccidial treatment category may be relevant. Consult a veterinarian before administering any medication.",
    ),
    dict(
        disease_name="Newcastle Disease", category="Viral",
        description="A highly contagious viral disease that can affect the respiratory, nervous and digestive systems of poultry.",
        reference_symptoms="Gasping or coughing\nGreenish watery diarrhoea\nTwisted neck or tremors\nDrop in egg production\nSudden deaths in the flock",
        general_care="Isolate sick birds immediately, limit visitors and movement of birds and equipment, and practise strict biosecurity.",
        referral_guidance="Supportive care may be relevant. Consult a veterinarian about disease confirmation and vaccination status; this disease may be notifiable in your country.",
    ),
    dict(
        disease_name="Salmonella", category="Bacterial",
        description="A bacterial infection (e.g. pullorum disease, fowl typhoid, paratyphoid) that can cause illness in young birds and be transmitted to humans.",
        reference_symptoms="Lethargy and drooping wings\nWhite or yellow diarrhoea\nPasting of the vent\nReduced feed intake\nHigh mortality in chicks",
        general_care="Practise strict hygiene, wash hands after handling birds, isolate sick birds and keep feed and water uncontaminated.",
        referral_guidance="Antibiotic treatment may require veterinary assessment and prescription. Do not self-administer antibiotics based solely on the AI prediction.",
    ),
]

MEDICATIONS = [
    ("Coccidiosis", "Anticoccidial agents (e.g. sulfonamide or amprolium class)", "Anticoccidial",
     "General reference only. The choice of product, dose and duration must be decided by a veterinarian."),
    ("Newcastle Disease", "Supportive care (electrolytes / vitamins)", "Supportive care",
     "There is no specific antiviral treatment. Vaccination status and confirmation must be assessed by a veterinarian."),
    ("Salmonella", "Antibacterial agents", "Antibiotic",
     "Antibiotics require veterinary assessment and prescription. Resistance and withdrawal periods apply."),
    ("Healthy", "None indicated", "None",
     "No medication is indicated by the AI prediction."),
]


def seed_knowledge(db: Session) -> None:
    for d in DISEASES:
        if not db.scalar(select(DiseaseKnowledge).where(DiseaseKnowledge.disease_name == d["disease_name"])):
            db.add(DiseaseKnowledge(**d))
    db.flush()
    for disease, name, cat, notes in MEDICATIONS:
        exists = db.scalar(select(MedicationReference).where(
            MedicationReference.disease_class == disease, MedicationReference.medicine_name == name))
        if not exists:
            db.add(MedicationReference(disease_class=disease, medicine_name=name, category=cat, usage_notes=notes))
    db.commit()


def seed_admin(db: Session) -> None:
    cfg = settings()
    if not cfg.admin_email or not cfg.admin_password:
        log.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set; no admin created.")
        return

    email = cfg.admin_email.lower().strip()
    existing_admin = db.scalar(select(User).where(User.email == email))
    if existing_admin is not None:
        existing_admin.full_name = cfg.admin_full_name
        existing_admin.role = "admin"
        existing_admin.password_hash = hash_password(cfg.admin_password)
        existing_admin.is_active = True
        db.commit()
        log.info("Administrator credentials refreshed from current environment settings.")
        return

    if db.scalar(select(User).where(User.role == "admin")):
        log.warning("An administrator already exists with a different email; leaving it unchanged.")
        return

    db.add(User(full_name=cfg.admin_full_name, role="admin", email=email,
                password_hash=hash_password(cfg.admin_password)))
    db.commit()
    log.info("Initial administrator created.")


def run() -> None:
    init_db()
    db = new_session()
    try:
        seed_knowledge(db)
        seed_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
    print("Database initialised and seeded.")
