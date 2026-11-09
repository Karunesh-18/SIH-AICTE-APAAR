from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import fail, get_current_user, require_roles
from app.api.schemas import Strict
from app.core.config import settings
from app.db.session import get_db, uow
from app.models.consent import FIELDS, PURPOSES, VERIFIER_STATUS, VERIFIER_TYPES
from app.models.enums import Role
from app.models.user import User
from app.services import ratelimit, verifiers
from app.services.errors import Conflict, NotFound

public = APIRouter(tags=["verifiers"])
admin = APIRouter(prefix="/admin", tags=["verifiers"])
admin_only = require_roles(Role.AICTE_ADMIN)
Purpose = Literal[PURPOSES]  # type: ignore[valid-type]
Field_ = Literal[FIELDS]  # type: ignore[valid-type]
OrgType = Literal[VERIFIER_TYPES]  # type: ignore[valid-type]
Status = Literal[VERIFIER_STATUS]  # type: ignore[valid-type]


class RegisterIn(Strict):
    org_name: str = Field(min_length=2, max_length=200)
    org_type: OrgType
    contact: str = Field(min_length=2, max_length=200)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    password: str = Field(min_length=10, max_length=72)  # 72: bcrypt ignores the rest
    requested_purposes: list[Purpose] = Field(min_length=1, max_length=len(PURPOSES))


class DecisionIn(Strict):
    note: str = Field(max_length=1000)

    @field_validator("note")
    @classmethod
    def _note(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a note is required")
        return v.strip()


class PolicyIn(DecisionIn):
    allowed_fields: list[Field_] = Field(max_length=len(FIELDS))


@public.post("/verifiers/register", status_code=202)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    who = f"register:{request.client.host if request.client else '-'}"
    if not ratelimit.take(who, settings.register_max_per_hour, timedelta(hours=1)):
        raise HTTPException(429, "Too many registrations. Try again later.")
    with uow(db):
        verifiers.register(db, **body.model_dump())
    # Same answer whether or not the email was already registered.
    return {"message": "Registration received. AICTE will review it; you can sign in once it "
                       "is approved."}


def _v(v, email) -> dict:
    return {"id": v.id, "org_name": v.org_name, "org_type": v.org_type, "contact": v.contact,
            "email": email, "requested_purposes": v.requested_purposes, "status": v.status,
            "decided_by": v.decided_by, "decision_note": v.decision_note,
            "created_at": v.created_at}


@admin.get("/verifiers")
def list_verifiers(status: Status | None = None, limit: int = Query(200, ge=1, le=500),
                   _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return {"items": [_v(v, e) for v, e in verifiers.list_verifiers(db, status)][:limit]}


def _decide(verifier_id: str, body: DecisionIn, approve: bool, user: User, db: Session):
    try:
        with uow(db):
            v = verifiers.decide(db, user, verifier_id, approve, body.note)
            email = db.get(User, v.user_id).email
    except (NotFound, Conflict) as e:
        raise fail(db, user, e, "verifier", verifier_id) from None
    return _v(v, email)


@admin.post("/verifiers/{verifier_id}/approve")
def approve(verifier_id: str, body: DecisionIn, user: User = Depends(admin_only),
            db: Session = Depends(get_db)):
    return _decide(verifier_id, body, True, user, db)


@admin.post("/verifiers/{verifier_id}/reject")
def reject(verifier_id: str, body: DecisionIn, user: User = Depends(admin_only),
           db: Session = Depends(get_db)):
    return _decide(verifier_id, body, False, user, db)


def _p(p) -> dict:
    return {"purpose": p.purpose, "allowed_fields": p.allowed_fields, "version": p.version,
            "note": p.note, "updated_at": p.updated_at}


@admin.get("/policies")
def list_policies(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return {"items": [_p(p) for p in verifiers.active_policies(db)], "fields": list(FIELDS)}


@public.get("/policies")
def read_policies(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read-only view for any signed-in role: what each purpose may release."""
    return {"items": [{"purpose": p.purpose, "allowed_fields": p.allowed_fields,
                       "version": p.version} for p in verifiers.active_policies(db)],
            "fields": list(FIELDS)}


@admin.put("/policies/{purpose}")
def put_policy(purpose: Purpose, body: PolicyIn, user: User = Depends(admin_only),
               db: Session = Depends(get_db)):
    with uow(db):
        p = verifiers.set_policy(db, user, purpose, body.allowed_fields, body.note)
    return _p(p)
