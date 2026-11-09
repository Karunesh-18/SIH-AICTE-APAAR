from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import fail, require_roles
from app.api.schemas import Strict
from app.db.session import get_db, uow
from app.models.consent import FIELDS, PURPOSES
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.user import User
from app.services import consents
from app.services.errors import Conflict, Forbidden, Invalid, NotFound

router = APIRouter(prefix="/consents", tags=["consents"])
recorder = require_roles(Role.AICTE_ADMIN, *INSTITUTION_ROLES)
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
Purpose = Literal[PURPOSES]  # type: ignore[valid-type]
Field_ = Literal[FIELDS]  # type: ignore[valid-type]


class ConsentIn(Strict):
    apaar_id: str = Field(min_length=1, max_length=32)
    purposes: list[Purpose] = Field(min_length=1, max_length=len(PURPOSES))
    fields: list[Field_] = Field(min_length=1, max_length=len(FIELDS))
    source: str = Field(min_length=1, max_length=64)
    expires_at: datetime


@router.post("", status_code=201)
def create(body: ConsentIn, user: User = Depends(recorder), db: Session = Depends(get_db)):
    try:
        with uow(db):
            c = consents.record(db, user, **body.model_dump())
    except (Forbidden, NotFound, Invalid) as e:
        raise fail(db, user, e, "consent", body.apaar_id[-4:]) from None
    return consents.out(db, user, c)


@router.delete("/{consent_id}")
def withdraw(consent_id: str, user: User = Depends(recorder), db: Session = Depends(get_db)):
    try:
        with uow(db):
            c = consents.withdraw(db, user, consent_id)
    except (Forbidden, NotFound, Conflict) as e:
        raise fail(db, user, e, "consent", consent_id) from None
    return consents.out(db, user, c)


@router.get("")
def list_consents(apaar: str | None = None, limit: int = Query(50, ge=1, le=200),
                  offset: int = Query(0, ge=0), user: User = Depends(reader),
                  db: Session = Depends(get_db)):
    rows = consents.list_scoped(db, user, apaar, limit, offset)
    return {"items": [consents.out(db, user, c) for c in rows]}


__all__ = ["HTTPException", "router"]
