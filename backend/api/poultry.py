from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_poultry_for_user, require_roles
from backend.database.session import get_db
from backend.models.models import Poultry, User
from backend.schemas.schemas import PoultryIn, PoultryOut, PoultryUpdate
from backend.services.audit import audit
from backend.services.report_service import poultry_code

router = APIRouter(prefix="/api/poultry", tags=["Poultry"])


def _out(p: Poultry) -> PoultryOut:
    return PoultryOut(poultry_id=p.poultry_id, poultry_code=poultry_code(p.poultry_id), user_id=p.user_id,
                      poultry_type=p.poultry_type, breed=p.breed, age=p.age, flock_size=p.flock_size,
                      production_type=p.production_type, health_history=p.health_history, created_at=p.created_at)


@router.post("", response_model=PoultryOut, status_code=201)
def create(body: PoultryIn, user: User = Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    p = Poultry(user_id=user.user_id, **body.model_dump())
    db.add(p)
    db.commit()
    audit(db, user.user_id, "poultry_created", "poultry", p.poultry_id)
    return _out(p)


@router.get("", response_model=list[PoultryOut])
def list_poultry(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Poultry).order_by(Poultry.poultry_id.desc())
    if user.role == "farmer":
        q = q.where(Poultry.user_id == user.user_id)
    elif user.role == "veterinarian":
        # vets see only poultry that has a case they may handle
        return [_out(p) for p in db.scalars(q) if any(c.assigned_vet_id in (None, user.user_id) for c in p.predictions)]
    return [_out(p) for p in db.scalars(q)]


@router.get("/{poultry_id}", response_model=PoultryOut)
def get_one(poultry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(get_poultry_for_user(db, poultry_id, user))


@router.put("/{poultry_id}", response_model=PoultryOut)
def update(poultry_id: int, body: PoultryUpdate, user: User = Depends(require_roles("farmer", "admin")),
           db: Session = Depends(get_db)):
    p = get_poultry_for_user(db, poultry_id, user, write=True)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(p, k, v)
    db.commit()
    audit(db, user.user_id, "poultry_updated", "poultry", p.poultry_id)
    return _out(p)


@router.delete("/{poultry_id}", status_code=204)
def delete(poultry_id: int, user: User = Depends(require_roles("farmer", "admin")), db: Session = Depends(get_db)):
    p = get_poultry_for_user(db, poultry_id, user, write=True)
    if p.predictions:  # protect clinical records
        raise HTTPException(409, "This poultry record has diagnosis history and cannot be deleted.")
    db.delete(p)
    db.commit()
    audit(db, user.user_id, "poultry_deleted", "poultry", poultry_id)
    return Response(status_code=204)
