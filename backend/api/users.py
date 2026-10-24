from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.core.security import hash_password, verify_password
from backend.database.session import get_db
from backend.models.models import User
from backend.schemas.schemas import UserOut, UserUpdate
from backend.services.audit import audit

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if data.get("new_password"):
        if not data.get("current_password") or not verify_password(data["current_password"], user.password_hash):
            raise HTTPException(400, "Current password is incorrect.")
        user.password_hash = hash_password(data["new_password"])
    for f in ("full_name", "contact_number", "location"):
        if f in data and data[f] is not None:
            setattr(user, f, data[f])
    if user.role == "veterinarian" and data.get("license_number"):
        user.license_number = data["license_number"]
    db.commit()
    audit(db, user.user_id, "profile_updated", "user", user.user_id)
    return user
