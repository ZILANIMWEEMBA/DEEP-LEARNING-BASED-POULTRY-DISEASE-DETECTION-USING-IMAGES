"""Shared fixtures. A TEST DOUBLE predictor is used only to exercise the application
workflow; it is never part of the application code and never used at runtime."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from machine_learning.inference.predictor import PoultryPredictor, build_result  # noqa: E402


class StubPredictor(PoultryPredictor):
    """Test double returning a fixed distribution (NOT a real model)."""
    def __init__(self, probs=(0.03, 0.91, 0.04, 0.02)):
        super().__init__(Path("/nonexistent"), Path("/nonexistent"))
        self.probs = np.array(probs)

    def is_available(self) -> bool:
        return True

    @property
    def version(self):
        return "test-stub"

    def predict(self, image_bytes: bytes) -> dict:
        return build_result(self.probs)


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "no_model.h5"))
    monkeypatch.setenv("CLASS_NAMES_PATH", str(tmp_path / "no_classes.json"))
    monkeypatch.setenv("MODEL_METADATA_PATH", str(tmp_path / "no_meta.json"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@test.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123!")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.60")
    from backend.core.config import reset_settings
    from backend.database.session import reset_engine
    from backend.services.model_service import reset_predictor
    reset_settings(); reset_engine(); reset_predictor()
    yield tmp_path
    reset_engine(); reset_settings(); reset_predictor()


@pytest.fixture()
def client(app_env):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services.model_service import get_predictor
    app.dependency_overrides[get_predictor] = lambda: StubPredictor()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def real_model_client(app_env):
    """Client WITHOUT the stub -> exercises 'model unavailable' behaviour."""
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c


def make_image(fmt="JPEG", size=(128, 128)) -> bytes:
    arr = np.random.default_rng(1).integers(0, 255, (*size, 3), dtype="uint8")
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, fmt)
    return buf.getvalue()


def register_login(client, email, role="farmer", name="Test User", password="Passw0rd!x", **extra):
    body = {"full_name": name, "email": email, "password": password, "role": role, **extra}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def farmer(client):
    return register_login(client, "farmer@test.com", "farmer", "Farmer One")


@pytest.fixture()
def vet(client):
    return register_login(client, "vet@test.com", "veterinarian", "Dr Vet", license_number="VET-123")


@pytest.fixture()
def admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def poultry_id(client, farmer):
    r = client.post("/api/poultry", json={"poultry_type": "Chicken", "breed": "Broiler", "age": 6, "flock_size": 50},
                    headers=farmer)
    assert r.status_code == 201, r.text
    return r.json()["poultry_id"]


def upload(client, headers, poultry_id, data=None, filename="bird.jpg"):
    return client.post("/api/predictions", headers=headers, data={"poultry_id": poultry_id, "symptoms": "bloody droppings"},
                       files={"file": (filename, data if data is not None else make_image(), "image/jpeg")})
