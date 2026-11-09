from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.schemas import Strict
from app.core import clock
from app.core.config import settings
from app.db.session import get_db, uow
from app.models.audit import AuditLog
from app.models.enums import Role
from app.models.notify import Outbox
from app.models.user import User
from app.services import anomaly, audit, clock_admin, notify, rules_admin, windows
from app.services.errors import Invalid, NotFound

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


@router.post("/audit/checkpoint")
def create_checkpoint(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        cp = audit.create_checkpoint(db, user)
    except Invalid as e:
        raise HTTPException(409, str(e)) from None
    return audit.checkpoint_out(cp)


@router.post("/dev/truncate-audit")
def truncate_audit(n: int = Query(3, ge=1, le=100), _: User = Depends(admin_only),
                   db: Session = Depends(get_db)):
    """Demo only: delete the last n audit rows, which the chain alone cannot detect."""
    if not settings.demo_mode:
        raise HTTPException(404, "Not found")
    with uow(db):  # raw delete, deliberately bypassing audit.append
        rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(n)).all()
        for r in rows:
            db.delete(r)
    return {"deleted": len(rows)}


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
    return {"offset_days": clock.get_offset_seconds() / 86400, "now": clock.now(),
            "demo_mode": settings.demo_mode}


@router.post("/clock")
def set_clock(body: ClockIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    seconds = clock_admin.set_clock(db, user, body.advance_days, body.reset)
    return {"offset_days": seconds / 86400, "now": clock.now(), "demo_mode": settings.demo_mode}


# ---- rule versions ------------------------------------------------------------------------------

def _version_out(v) -> dict:
    return {"id": v.id, "rule_code": v.rule_code, "version_no": v.version_no,
            "enabled": v.enabled, "params": v.params, "hard_stop": v.hard_stop,
            "message_en": v.message_en, "message_hi": v.message_hi, "note": v.note,
            "is_active": v.is_active, "created_by": v.created_by, "created_at": v.created_at}


class _Note(Strict):
    note: str

    @field_validator("note")
    @classmethod
    def _required(cls, v):
        if not v.strip():
            raise ValueError("a note is required")
        return v.strip()


class RuleUpdateIn(_Note):
    params: dict | None = None
    message_en: str | None = None
    message_hi: str | None = None
    enabled: bool | None = None
    hard_stop: bool | None = None


class RevertIn(_Note):
    to_version: int


def _guard(fn, *a):
    try:
        return fn(*a)
    except rules_admin.NotFound as e:
        raise HTTPException(404, str(e)) from None


@router.get("/rules")
def list_rules(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [{"code": r.code, "scope": r.scope, "title": r.title,
             "active": _version_out(v) if v else None} for r, v in rules_admin.list_rules(db)]


@router.get("/rules/{code}/versions")
def rule_versions(code: str, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [_version_out(v) for v in _guard(rules_admin.versions, db, code)]


@router.get("/rules/{code}/diff")
def rule_diff(code: str, from_: int = Query(alias="from"), to: int = Query(),
              _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _guard(rules_admin.diff, db, code, from_, to)


@router.put("/rules/{code}")
def update_rule(code: str, body: RuleUpdateIn, user: User = Depends(admin_only),
                db: Session = Depends(get_db)):
    changes = body.model_dump(exclude={"note"}, exclude_none=True)
    return _version_out(_guard(rules_admin.update, db, user, code, changes, body.note))


@router.post("/rules/{code}/revert")
def revert_rule(code: str, body: RevertIn, user: User = Depends(admin_only),
                db: Session = Depends(get_db)):
    return _version_out(_guard(rules_admin.revert, db, user, code, body.to_version, body.note))


# ---- submission windows and scheduled rules -----------------------------------------------------

class LadderStep(Strict):
    step: str
    offset_hours: int
    audience: Literal["institution", "officer", "admin"] = "institution"


class WindowIn(Strict):
    cycle_year: int
    institution_type: Literal["ENGINEERING", "MANAGEMENT", "PHARMACY", "OTHER"] | None = None
    opens_at: datetime
    closes_at: datetime
    ladder: list[LadderStep]

    @model_validator(mode="after")
    def _valid(self):
        self.opens_at, self.closes_at = (
            d if d.tzinfo else d.replace(tzinfo=UTC) for d in (self.opens_at, self.closes_at))
        if self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be after opens_at")
        if len({s.step for s in self.ladder}) != len(self.ladder):
            raise ValueError("ladder step names must be unique")
        return self


@router.get("/windows")
def list_windows(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [windows.window_out(w) for w in windows.list_windows(db)]


@router.post("/windows", status_code=201)
def create_window(body: WindowIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return windows.window_out(windows.save(db, user, body.model_dump()))


@router.put("/windows/{window_id}")
def update_window(window_id: str, body: WindowIn, user: User = Depends(admin_only),
                  db: Session = Depends(get_db)):
    try:
        return windows.window_out(windows.save(db, user, body.model_dump(), window_id))
    except NotFound as e:
        raise HTTPException(404, str(e)) from None


@router.post("/windows/run-cycle")
def run_cycle(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return windows.run_cycle(db, actor=user)


@router.post("/outbox/dispatch")
def dispatch_outbox(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Send queued email now (the scheduler does this on a timer). Retries failures."""
    out = notify.dispatch_now(db)
    out["pending"] = db.scalar(select(func.count()).select_from(Outbox).where(
        Outbox.dispatched_at.is_(None), Outbox.attempts < notify.MAX_ATTEMPTS)) or 0
    return out


@router.post("/anomaly/run")
def run_anomaly(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    raised = anomaly.run_all(db, clock.now(), user)
    notify.dispatch_now(db)
    return {"raised": len(raised), "flags": [{"id": f.id, "rule": f.rule_code} for f in raised]}
