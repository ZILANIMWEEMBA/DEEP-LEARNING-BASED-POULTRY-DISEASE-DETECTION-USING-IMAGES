"""FastAPI application entry point.

Run:  uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
Docs: /docs  and  /redoc
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import (admin, auth, consultations, medications, notifications, poultry, predictions,
                         reports, users, veterinary)
from backend.core.config import settings
from backend.core.logging_config import setup_logging
from backend.database.session import init_db, new_session
from backend.middleware.error_handlers import register_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = settings()  # fails fast if SECRET_KEY is missing
    setup_logging()
    cfg.image_dir.mkdir(parents=True, exist_ok=True)
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    from database.seed_data import seed_admin, seed_knowledge
    db = new_session()
    try:
        seed_knowledge(db)
        seed_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Poultry Disease Detection & Veterinary Support API",
    description=("AI-assisted poultry health decision-support with veterinary human-in-the-loop review. "
                 "**AI predictions are not diagnoses and AI care suggestions are not prescriptions.**"),
    version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
                   allow_methods=["*"], allow_headers=["*"])
register_handlers(app)

for r in (auth, users, poultry, predictions, reports, consultations, veterinary, medications, notifications, admin):
    app.include_router(r.router)


@app.get("/health", tags=["System"])
def health():
    from backend.services.model_service import get_predictor
    return {"status": "ok", "model_available": get_predictor().is_available()}
