"""ORM models. Mirrors the ER design in docs/database.md and database/schema.sql."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)  # farmer|veterinarian|admin
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    contact_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)  # vets only
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    poultry: Mapped[list["Poultry"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Poultry(Base):
    __tablename__ = "poultry"
    poultry_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    poultry_type: Mapped[str] = mapped_column(String(50))  # chicken, duck, ...
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)  # weeks
    flock_size: Mapped[int] = mapped_column(Integer, default=1)
    production_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # layer/broiler/...
    health_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner: Mapped[User] = relationship(back_populates="poultry")
    predictions: Mapped[list["PredictionHistory"]] = relationship(back_populates="poultry", cascade="all, delete-orphan")


class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    image_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)  # generated, never user-supplied
    original_extension: Mapped[str] = mapped_column(String(10))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PredictionHistory(Base):
    """Core table. One row == one case (case_id = CASE-<prediction_id>)."""
    __tablename__ = "prediction_history"
    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poultry_id: Mapped[int] = mapped_column(ForeignKey("poultry.poultry_id", ondelete="CASCADE"), index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_images.image_id"), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(100))
    predicted_class: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    healthy_prob: Mapped[float] = mapped_column(Float)
    coccidiosis_prob: Mapped[float] = mapped_column(Float)
    newcastle_prob: Mapped[float] = mapped_column(Float)
    salmonella_prob: Mapped[float] = mapped_column(Float)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    farmer_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending Review", index=True)
    assigned_vet_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True, index=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    poultry: Mapped[Poultry] = relationship(back_populates="predictions")
    image: Mapped[UploadedImage | None] = relationship()
    review: Mapped["VeterinaryReview | None"] = relationship(back_populates="prediction", uselist=False)

    @property
    def case_id(self) -> str:
        return f"CASE-{self.prediction_id:05d}"


class VeterinaryReview(Base):
    __tablename__ = "veterinary_review"
    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction_history.prediction_id", ondelete="CASCADE"), unique=True)
    vet_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    diagnosis: Mapped[str] = mapped_column(String(200))
    diagnosis_action: Mapped[str] = mapped_column(String(20))  # confirmed | revised
    clinical_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescription: Mapped[str | None] = mapped_column(String(255), nullable=True)  # medication name
    dosage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    additional_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    license_info: Mapped[str | None] = mapped_column(String(100), nullable=True)
    veterinary_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    prediction: Mapped[PredictionHistory] = relationship(back_populates="review")
    veterinarian: Mapped[User] = relationship()


class DiseaseKnowledge(Base):
    __tablename__ = "disease_knowledge"
    disease_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disease_name: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    reference_symptoms: Mapped[str] = mapped_column(Text)  # newline-separated
    general_care: Mapped[str] = mapped_column(Text)
    referral_guidance: Mapped[str] = mapped_column(Text)

    medications: Mapped[list["MedicationReference"]] = relationship(back_populates="disease")


class MedicationReference(Base):
    __tablename__ = "medication_reference"
    medication_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disease_class: Mapped[str] = mapped_column(ForeignKey("disease_knowledge.disease_name"), index=True)
    medicine_name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(100))
    usage_notes: Mapped[str] = mapped_column(Text)  # general info only - NO dosage

    disease: Mapped[DiseaseKnowledge] = relationship(back_populates="medications")


class Consultation(Base):
    __tablename__ = "consultations"
    consultation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction_history.prediction_id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    message: Mapped[str] = mapped_column(Text)
    is_request: Mapped[bool] = mapped_column(Boolean, default=False)  # initial request for review
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sender: Mapped[User] = relationship()


class Report(Base):
    __tablename__ = "reports"
    report_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction_history.prediction_id", ondelete="CASCADE"), index=True)
    report_type: Mapped[str] = mapped_column(String(20))  # ai | veterinary
    content_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (Index("ix_reports_pred_type", "prediction_id", "report_type"),)


class Notification(Base):
    __tablename__ = "notifications"
    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("prediction_history.prediction_id", ondelete="SET NULL"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
