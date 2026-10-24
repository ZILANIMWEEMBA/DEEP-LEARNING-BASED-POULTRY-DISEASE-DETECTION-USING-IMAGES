from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.security import create_access_token, hash_password, verify_password
from backend.database.session import get_db
from backend.models.models import User
from backend.schemas.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from backend.services.audit import audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201, summary="Register a farmer or veterinarian")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(full_name=body.full_name.strip(), email=email, role=body.role,
                contact_number=body.contact_number, location=body.location,
                license_number=(body.license_number or None), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    audit(db, user.user_id, "user_registered", "user", user.user_id, {"role": user.role})
    return user


@router.post("/login", response_model=TokenOut, summary="Log in and receive a JWT")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        audit(db, user.user_id if user else None, "login_failed", "user", user.user_id if user else None,
              {"email": body.email.lower()})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")
    audit(db, user.user_id, "login", "user", user.user_id)
    return TokenOut(access_token=create_access_token(user.user_id, user.role), user=UserOut.model_validate(user))
