"""Audit trail (DB) + structured log line."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.core.logging_config import get_logger
from backend.models.models import AuditLog

log = get_logger("audit")


def audit(db: Session, user_id: int | None, action: str, entity: str,
          entity_id: Any = None, details: dict | str | None = None, commit: bool = True) -> None:
    text = json.dumps(details, default=str) if isinstance(details, dict) else details
    db.add(AuditLog(user_id=user_id, action=action, entity=entity,
                    entity_id=None if entity_id is None else str(entity_id), details=text))
    if commit:
        db.commit()
    log.info(action, extra={"extra_data": {"user_id": user_id, "entity": entity, "entity_id": entity_id}})
