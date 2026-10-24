from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.core.exceptions import NotFound
from backend.database.session import get_db
from backend.models.models import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _out(n: Notification) -> dict:
    return {"notification_id": n.notification_id, "title": n.title, "message": n.message,
            "prediction_id": n.prediction_id, "is_read": n.is_read, "created_at": n.created_at.isoformat()}


@router.get("")
def list_notifications(unread_only: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.user_id).order_by(Notification.created_at.desc())
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    return [_out(n) for n in db.scalars(q.limit(200))]


@router.put("/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.user_id:
        raise NotFound("Notification not found.")
    n.is_read = True
    db.commit()
    return _out(n)
