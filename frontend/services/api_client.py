"""Thin REST client for the FastAPI backend (Streamlit -> FastAPI)."""
from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from frontend.utils.constants import API_BASE_URL


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.message, self.status = message, status


def _headers() -> dict[str, str]:
    tok = st.session_state.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _request(method: str, path: str, **kw) -> requests.Response:
    try:
        r = requests.request(method, f"{API_BASE_URL}{path}", headers=_headers(), timeout=60, **kw)
    except requests.ConnectionError:
        raise ApiError("Cannot reach the server. Please make sure the backend is running.") from None
    except requests.Timeout:
        raise ApiError("The server took too long to respond. Please try again.") from None
    if r.status_code == 401 and st.session_state.get("token"):
        st.session_state.clear()
        raise ApiError("Your session has expired. Please log in again.", 401)
    if not r.ok:
        try:
            detail = r.json().get("detail", "Request failed.")
            if isinstance(detail, list):
                detail = "; ".join(str(d.get("msg", d)) for d in detail)
        except ValueError:
            detail = "Request failed."
        raise ApiError(str(detail), r.status_code)
    return r


def get(path: str, **params) -> Any:
    return _request("GET", path, params={k: v for k, v in params.items() if v is not None}).json()


def post(path: str, json: dict | None = None, **kw) -> Any:
    r = _request("POST", path, json=json, **kw)
    return r.json() if r.content else None


def put(path: str, json: dict | None = None) -> Any:
    return _request("PUT", path, json=json).json()


def delete(path: str) -> None:
    _request("DELETE", path)


def get_bytes(path: str) -> bytes:
    return _request("GET", path).content


def upload_prediction(poultry_id: int, filename: str, data: bytes, mime: str,
                      symptoms: str, observations: str) -> dict:
    return _request("POST", "/api/predictions",
                    data={"poultry_id": poultry_id, "symptoms": symptoms, "observations": observations},
                    files={"file": (filename, data, mime)}).json()
