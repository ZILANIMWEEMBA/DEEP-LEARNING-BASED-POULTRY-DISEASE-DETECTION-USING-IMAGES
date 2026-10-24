"""Pydantic request/response schemas (OpenAPI-documented)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ---------------------------------------------------------------- auth/users
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["farmer", "veterinarian"] = "farmer"
    contact_number: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=255)
    license_number: Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _vet_needs_license(self):
        if self.role == "veterinarian" and not (self.license_number or "").strip():
            raise ValueError("Veterinarians must provide a professional license/registration number.")
        return self

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        if v.isalpha() or v.isdigit():
            raise ValueError("Password must mix letters and numbers/symbols.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    role: str
    email: str
    contact_number: Optional[str] = None
    location: Optional[str] = None
    license_number: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    contact_number: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=255)
    license_number: Optional[str] = Field(default=None, max_length=100)
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class AdminUserCreate(RegisterIn):
    role: Literal["farmer", "veterinarian", "admin"] = "farmer"  # type: ignore[assignment]


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    role: Optional[Literal["farmer", "veterinarian", "admin"]] = None


# ------------------------------------------------------------------ poultry
class PoultryIn(BaseModel):
    poultry_type: str = Field(min_length=2, max_length=50)
    breed: Optional[str] = Field(default=None, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=500, description="Age in weeks")
    flock_size: int = Field(default=1, ge=1, le=1_000_000)
    production_type: Optional[str] = Field(default=None, max_length=50)
    health_history: Optional[str] = Field(default=None, max_length=4000)


class PoultryUpdate(BaseModel):
    poultry_type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    breed: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=500)
    flock_size: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    production_type: Optional[str] = None
    health_history: Optional[str] = Field(default=None, max_length=4000)


class PoultryOut(PoultryIn):
    model_config = ConfigDict(from_attributes=True)
    poultry_id: int
    poultry_code: str
    user_id: int
    created_at: datetime


# ------------------------------------------------------------------ vet flow
class ReviewIn(BaseModel):
    prediction_id: int
    diagnosis: str = Field(min_length=2, max_length=200)
    diagnosis_action: Literal["confirmed", "revised"]
    clinical_assessment: Optional[str] = Field(default=None, max_length=4000)
    treatment_plan: Optional[str] = Field(default=None, max_length=4000)
    prescription: Optional[str] = Field(default=None, max_length=255, description="Medication name (veterinarian only)")
    dosage: Optional[str] = Field(default=None, max_length=255)
    frequency: Optional[str] = Field(default=None, max_length=255)
    duration: Optional[str] = Field(default=None, max_length=255)
    additional_instructions: Optional[str] = Field(default=None, max_length=4000)
    follow_up_date: Optional[datetime] = None
    veterinary_comments: Optional[str] = Field(default=None, max_length=4000)
    mark_completed: bool = False

    @model_validator(mode="after")
    def _prescription_complete(self):
        if self.prescription and self.prescription.strip():
            missing = [n for n in ("dosage", "frequency", "duration") if not (getattr(self, n) or "").strip()]
            if missing:
                raise ValueError(f"A prescription requires: {', '.join(missing)}.")
        return self


class ReviewUpdate(BaseModel):
    diagnosis: Optional[str] = Field(default=None, min_length=2, max_length=200)
    diagnosis_action: Optional[Literal["confirmed", "revised"]] = None
    clinical_assessment: Optional[str] = None
    treatment_plan: Optional[str] = None
    prescription: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    additional_instructions: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    veterinary_comments: Optional[str] = None
    mark_completed: Optional[bool] = None


class CaseStatusIn(BaseModel):
    status: Literal["Under Review", "Follow-up Required", "Completed", "Rejected / Insufficient Information"]
    comment: Optional[str] = Field(default=None, max_length=2000)


class ConsultationIn(BaseModel):
    prediction_id: int
    message: str = Field(min_length=2, max_length=4000)
    is_request: bool = False


class ConsultationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    consultation_id: int
    prediction_id: int
    sender_id: int
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    message: str
    is_request: bool
    created_at: datetime


class ReportCreate(BaseModel):
    prediction_id: int
    report_type: Literal["ai", "veterinary"]


# ------------------------------------------------------------------ reference
class MedicationIn(BaseModel):
    disease_class: str
    medicine_name: str = Field(min_length=2, max_length=150)
    category: str = Field(min_length=2, max_length=100)
    usage_notes: str = Field(min_length=2, max_length=2000)


class DiseaseUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    reference_symptoms: Optional[str] = None
    general_care: Optional[str] = None
    referral_guidance: Optional[str] = None


class BroadcastIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=2, max_length=2000)
    role: Optional[Literal["farmer", "veterinarian", "admin"]] = None


TokenOut.model_rebuild()
