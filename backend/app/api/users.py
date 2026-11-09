"""User management. AICTE admin: any user. Institution admin: staff of its own institution only."""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.api.deps import fail, institution_or_403, refuse, require_roles
from app.api.schemas import Strict
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.services import errors as E
from app.services import users

admin_router = APIRouter(prefix="/admin/users", tags=["users"])
staff_router = APIRouter(prefix="/institutions/{institution_id}/staff", tags=["users"])
admin_only = require_roles(Role.AICTE_ADMIN)
inst_admin_only = require_roles(Role.INSTITUTION_ADMIN)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v) or len(v) > 200:
        raise ValueError("not a valid email address")
    return v


class StaffIn(Strict):
    email: str
    full_name: str = Field(min_length=1, max_length=120)
    password: str | None = Field(None, max_length=200)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return _email(v)


class UserIn(StaffIn):
    role: Literal["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF"]
    institution_id: str | None = None
    regions: list[str] = Field(default_factory=list)


class UserPatch(Strict):
    role: Literal["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(None, min_length=1, max_length=120)
    institution_id: str | None = None
    regions: list[str] | None = None

    @model_validator(mode="after")
    def _something(self):
        if not self.model_fields_set:
            raise ValueError("send at least one field to change")
        return self


class StaffPatch(Strict):
    is_active: bool | None = None
    full_name: str | None = Field(None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def _something(self):
        if not self.model_fields_set:
            raise ValueError("send at least one field to change")
        return self


def _run(db: Session, actor: User, fn, *a, **kw):
    try:
        return fn(db, actor, *a, **kw)
    except (E.NotFound, E.Conflict, E.Invalid) as e:
        raise fail(db, actor, e, "user", "n/a") from None


def _created(db: Session, actor: User, **kw):
    u, temp = _run(db, actor, users.create, **kw)
    return {"user": users.out(db, u)} | ({"temporary_password": temp} if temp else {})


# ---- AICTE admin -------------------------------------------------------------------------------

@admin_router.get("")
def list_all(role: str | None = None, institution: str | None = None, active: bool | None = None,
             q: str | None = Query(None, max_length=100),
             limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
             _: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows, total = users.list_users(db, role=role, institution_id=institution, active=active, q=q,
                                   limit=limit, offset=offset)
    return {"items": [users.out(db, u) for u in rows], "total": total}


@admin_router.post("", status_code=201)
def create_user(body: UserIn, actor: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _created(db, actor, **body.model_dump())


@admin_router.patch("/{user_id}")
def patch_user(user_id: str, body: UserPatch, actor: User = Depends(admin_only),
               db: Session = Depends(get_db)):
    u = _run(db, actor, users.update, user_id, body.model_dump(exclude_unset=True))
    return users.out(db, u)


@admin_router.post("/{user_id}/reset-password")
def reset_user_password(user_id: str, actor: User = Depends(admin_only),
                        db: Session = Depends(get_db)):
    u, temp = _run(db, actor, users.reset_password, user_id)
    return {"user": users.out(db, u), "temporary_password": temp}


# ---- institution admin: own staff --------------------------------------------------------------

def _own(institution_id: str, actor: User, db: Session) -> str:
    """The path institution must be the caller's own, or the attempt is refused and audited."""
    if institution_id != actor.institution_id:
        refuse(db, actor, "institution", institution_id)
        raise HTTPException(403, "You can only manage staff of your own institution")
    return institution_or_403(db, actor, institution_id).id


@staff_router.get("")
def list_staff(institution_id: str, active: bool | None = None,
               limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               actor: User = Depends(inst_admin_only), db: Session = Depends(get_db)):
    inst = _own(institution_id, actor, db)
    rows, total = users.list_users(db, staff_of=inst, active=active, limit=limit, offset=offset)
    return {"items": [users.out(db, u) for u in rows], "total": total}


@staff_router.post("", status_code=201)
def create_staff(institution_id: str, body: StaffIn, actor: User = Depends(inst_admin_only),
                 db: Session = Depends(get_db)):
    inst = _own(institution_id, actor, db)
    return _created(db, actor, **body.model_dump(), role="INSTITUTION_STAFF", institution_id=inst)


@staff_router.patch("/{user_id}")
def patch_staff(institution_id: str, user_id: str, body: StaffPatch,
                actor: User = Depends(inst_admin_only), db: Session = Depends(get_db)):
    inst = _own(institution_id, actor, db)
    u = _run(db, actor, users.update, user_id, body.model_dump(exclude_unset=True),
             institution_id=inst)
    return users.out(db, u)


@staff_router.delete("/{user_id}")
def deactivate_staff(institution_id: str, user_id: str, actor: User = Depends(inst_admin_only),
                     db: Session = Depends(get_db)):
    """Deactivates; the account and its audit history stay."""
    inst = _own(institution_id, actor, db)
    u = _run(db, actor, users.update, user_id, {"is_active": False}, institution_id=inst)
    return users.out(db, u)


@staff_router.post("/{user_id}/reset-password")
def reset_staff_password(institution_id: str, user_id: str,
                         actor: User = Depends(inst_admin_only), db: Session = Depends(get_db)):
    inst = _own(institution_id, actor, db)
    u, temp = _run(db, actor, users.reset_password, user_id, institution_id=inst)
    return {"user": users.out(db, u), "temporary_password": temp}
