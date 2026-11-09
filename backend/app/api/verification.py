from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import fail, require_roles
from app.api.schemas import Strict
from app.core.config import settings
from app.db.session import get_db, uow
from app.models.consent import FIELDS, PURPOSES
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.user import User
from app.services import notify, ratelimit, signing, verification
from app.services.errors import Conflict, Forbidden, NotFound, RateLimited

router = APIRouter(tags=["verification"])
verifier_only = require_roles(Role.VERIFIER)
reader = require_roles(Role.VERIFIER, *AICTE_ROLES, *INSTITUTION_ROLES)
revoker = require_roles(Role.AICTE_ADMIN, Role.VERIFIER, *INSTITUTION_ROLES)
Purpose = Literal[PURPOSES]  # type: ignore[valid-type]
Field_ = Literal[FIELDS]  # type: ignore[valid-type]


class VerificationIn(Strict):
    apaar_id: str = Field(min_length=1, max_length=32)
    purpose: Purpose
    fields: list[Field_] = Field(min_length=1, max_length=len(FIELDS))


@router.post("/verifications")
def create(body: VerificationIn, user: User = Depends(verifier_only),
           db: Session = Depends(get_db)):
    try:
        with uow(db):
            out = verification.request_verification(db, user, **body.model_dump())
    except (Forbidden, RateLimited) as e:
        raise fail(db, user, e, "verification_request", "new") from None
    notify.dispatch_now(db)
    return out


@router.get("/verifications")
def list_verifications(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                       user: User = Depends(reader), db: Session = Depends(get_db)):
    return {"items": verification.list_scoped(db, user, limit, offset)}


@router.get("/verifications/{request_id}")
def get_verification(request_id: str, user: User = Depends(reader),
                     db: Session = Depends(get_db)):
    try:
        with uow(db):
            return verification.get_one(db, user, request_id)
    except (Forbidden, NotFound) as e:
        raise fail(db, user, e, "verification_request", request_id) from None


@router.post("/verifications/{request_id}/revoke")
def revoke(request_id: str, user: User = Depends(revoker), db: Session = Depends(get_db)):
    try:
        with uow(db):
            row = verification.revoke(db, user, request_id)
    except (Forbidden, NotFound, Conflict) as e:
        raise fail(db, user, e, "verification_request", request_id) from None
    return {"id": row.id, "revoked_at": row.revoked_at}


# Public: no login. The token is the credential, and it only proves itself.
@router.get("/verify/public-key")
def public_key():
    return {"pem": signing.public_pem(), "jwk": signing.public_jwk(), "alg": signing.ALG}


@router.get("/verify/{token}")
def check(token: str, request: Request, db: Session = Depends(get_db)):
    who = f"check:{request.client.host if request.client else '-'}"
    if not ratelimit.take(who, settings.check_max_per_minute, timedelta(minutes=1)):
        raise HTTPException(429, "Too many checks. Try again shortly.")
    with uow(db):
        return verification.check(db, token)
