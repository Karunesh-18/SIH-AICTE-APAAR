from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import institution_or_403, require_roles
from app.api.schemas import Strict
from app.db.session import get_db
from app.models.enums import Role
from app.models.system import ApiKey
from app.models.user import User
from app.services import apikeys

router = APIRouter(prefix="/institutions/{institution_id}/api-keys", tags=["api-keys"])
key_admin = require_roles(Role.AICTE_ADMIN, Role.INSTITUTION_ADMIN)


class KeyIn(Strict):
    name: str


def _out(k: ApiKey) -> dict:
    return {"id": k.id, "name": k.name, "prefix": k.prefix, "scope": k.scope,
            "created_at": k.created_at, "last_used_at": k.last_used_at,
            "revoked_at": k.revoked_at}


@router.post("", status_code=201)
def create_key(institution_id: str, body: KeyIn, user: User = Depends(key_admin),
               db: Session = Depends(get_db)):
    institution_or_403(db, user, institution_id)
    key, token = apikeys.create(db, user, institution_id, body.name.strip() or "key")
    return _out(key) | {"key": token}  # the only time the token is shown


@router.get("")
def list_keys(institution_id: str, user: User = Depends(key_admin), db: Session = Depends(get_db)):
    institution_or_403(db, user, institution_id)
    return [_out(k) for k in apikeys.list_keys(db, institution_id)]


@router.delete("/{key_id}")
def revoke_key(institution_id: str, key_id: str, user: User = Depends(key_admin),
               db: Session = Depends(get_db)):
    institution_or_403(db, user, institution_id)
    key = db.get(ApiKey, key_id)
    if key is None or key.institution_id != institution_id:
        raise HTTPException(404, "API key not found")
    return _out(apikeys.revoke(db, user, key))
