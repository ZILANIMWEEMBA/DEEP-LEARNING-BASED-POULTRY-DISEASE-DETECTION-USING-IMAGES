"""Central configuration. All values come from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Canonical class order. This is the ONLY definition used by training,
# inference, database storage, reports and the frontend.
CLASS_NAMES: list[str] = ["Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"]
# Folder names on disk (dataset/raw/<folder>) in the same canonical order.
CLASS_FOLDERS: list[str] = ["Healthy", "Coccidiosis", "Newcastle_Disease", "Salmonella"]

ROLES = ("farmer", "veterinarian", "admin")

CASE_STATUSES = (
    "Pending Review",
    "Under Review",
    "Diagnosis Confirmed",
    "Diagnosis Revised",
    "Treatment Issued",
    "Follow-up Required",
    "Completed",
    "Rejected / Insufficient Information",
)

AI_DISCLAIMER_TITLE = "AI Care Suggestion – Not a Prescription"
AI_DISCLAIMER_TEXT = (
    "AI prediction is for decision-support purposes only. Final diagnosis and "
    "treatment must be confirmed by a qualified veterinarian."
)
CONFIDENCE_NOTE = (
    "This confidence reflects the model's classification output and does not "
    "confirm a veterinary diagnosis."
)
LOW_CONFIDENCE_MESSAGE = (
    "Low-confidence AI prediction. Veterinary assessment is strongly recommended."
)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'database' / 'poultry.db'}"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")))
    model_path: Path = field(default_factory=lambda: _path(os.getenv("MODEL_PATH", "./model/poultry_mobilenetv2.h5")))
    class_names_path: Path = field(default_factory=lambda: _path(os.getenv("CLASS_NAMES_PATH", "./model/class_names.json")))
    model_metadata_path: Path = field(default_factory=lambda: _path(os.getenv("MODEL_METADATA_PATH", "./model/model_metadata.json")))
    upload_dir: Path = field(default_factory=lambda: _path(os.getenv("UPLOAD_DIR", "./uploads")))
    reports_dir: Path = field(default_factory=lambda: _path("./reports"))
    max_upload_bytes: int = field(default_factory=lambda: int(float(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024))
    confidence_threshold: float = field(default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD", "0.60")))
    allowed_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png")
    min_image_side: int = 64
    admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", ""))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    admin_full_name: str = field(default_factory=lambda: os.getenv("ADMIN_FULL_NAME", "System Administrator"))
    log_dir: Path = field(default_factory=lambda: _path("./logs"))

    @property
    def image_dir(self) -> Path:
        return self.upload_dir / "poultry_images"


_settings: Settings | None = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        s = Settings()
        if not s.secret_key:
            raise RuntimeError(
                "SECRET_KEY is not set. Copy .env.example to .env and set a strong SECRET_KEY."
            )
        _settings = s
    return _settings


def reset_settings() -> None:
    """Used by tests to re-read the environment."""
    global _settings
    _settings = None
