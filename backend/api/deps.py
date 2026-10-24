"""Authentication/authorisation dependencies and record-level access control."""
from __future__ import annotations

from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.exceptions import Forbidden, NotFound
from backend.core.security import decode_access_token
from backend.database.session import get_db
from backend.models.models import Poultry, PredictionHistory, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.",
                                 headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action.")
        return user
    return checker


# ------------------------------------------------------- record-level access
def get_prediction_for_user(db: Session, prediction_id: int, user: User) -> PredictionHistory:
    pred = db.get(PredictionHistory, prediction_id)
    if pred is None:
        raise NotFound("Case not found.")
    if user.role == "admin":
        return pred
    if user.role == "farmer":
        if pred.poultry.user_id != user.user_id:
            raise NotFound("Case not found.")  # do not reveal existence
        return pred
    if user.role == "veterinarian":
        if pred.assigned_vet_id in (None, user.user_id):
            return pred
        raise Forbidden("This case is assigned to another veterinarian.")
    raise Forbidden("Access denied.")


def get_poultry_for_user(db: Session, poultry_id: int, user: User, write: bool = False) -> Poultry:
    pt = db.get(Poultry, poultry_id)
    if pt is None:
        raise NotFound("Poultry record not found.")
    if user.role == "admin":
        return pt
    if user.role == "farmer":
        if pt.user_id != user.user_id:
            raise NotFound("Poultry record not found.")
        return pt
    if user.role == "veterinarian" and not write:
        has_case = any(p.assigned_vet_id in (None, user.user_id) for p in pt.predictions)
        if has_case:
            return pt
    raise Forbidden("Access denied.")
