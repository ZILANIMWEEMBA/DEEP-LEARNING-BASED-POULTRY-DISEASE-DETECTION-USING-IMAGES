"""Notification helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.models import Notification, User


def notify(db: Session, user_id: int, title: str, message: str, prediction_id: int | None = None) -> None:
    db.add(Notification(user_id=user_id, title=title, message=message, prediction_id=prediction_id))


def notify_role(db: Session, role: str, title: str, message: str, prediction_id: int | None = None) -> None:
    for uid in db.scalars(select(User.user_id).where(User.role == role, User.is_active.is_(True))):
        notify(db, uid, title, message, prediction_id)
