from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.schemas import Strict
from app.core import clock
from app.core.config import settings
from app.db.session import get_db, uow
from app.models.audit import AuditLog
from app.models.enums import Role
from app.models.user import User
from app.services import audit, clock_admin

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_roles(Role.AICTE_ADMIN)


class ClockIn(Strict):
    advance_days: float | None = None
    reset: bool = False

    @model_validator(mode="after")
    def _one_action(self):
        if not self.reset and self.advance_days is None:
            raise ValueError("send advance_days or reset")
        return self


@router.get("/audit")
def list_audit(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
               _: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    ).all()
    total = db.scalar(select(func.count()).select_from(AuditLog))
    items = [{
        "id": r.id, "occurred_at": r.occurred_at, "actor_id": r.actor_id,
        "actor_role": r.actor_role, "action": r.action, "entity_type": r.entity_type,
        "entity_id": r.entity_id, "before": r.before, "after": r.after,
    } for r in rows]
    return {"items": items, "total": total}


@router.post("/audit/verify")
def verify_audit(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return audit.verify(db)


@router.post("/dev/tamper-audit")
def tamper_audit(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Demo only: edit one audit row directly so the verify call has something to find."""
    if not settings.demo_mode:
        raise HTTPException(404, "Not found")
    row = db.scalars(select(AuditLog).order_by(AuditLog.id).limit(1)).first()
    if row is None:
        raise HTTPException(409, "No audit entries to tamper with")
    with uow(db):  # raw edit, deliberately bypassing audit.append
        row.after = {"tampered": True}
    return {"tampered_id": row.id}


@router.get("/clock")
def get_clock(_: User = Depends(admin_only)):
    return {"offset_days": clock.get_offset_seconds() / 86400, "now": clock.now()}


@router.post("/clock")
def set_clock(body: ClockIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    seconds = clock_admin.set_clock(db, user, body.advance_days, body.reset)
    return {"offset_days": seconds / 86400, "now": clock.now()}
