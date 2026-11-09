"""Per-institution API keys. The token is shown once; only its sha256 is stored (the token is
256 bits of randomness, so a plain hash is enough: there is nothing to brute-force)."""
import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.db.session import uow
from app.models.system import ApiKey
from app.models.user import User
from app.services import audit

SCOPE = "records:submit"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(db: Session, actor: User, institution_id: str, name: str) -> tuple[ApiKey, str]:
    token = "wmk_" + secrets.token_urlsafe(32)
    with uow(db):
        key = ApiKey(institution_id=institution_id, name=name, prefix=token[:8],
                     key_hash=_hash(token), scope=SCOPE, created_by=actor.id)
        db.add(key)
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="APIKEY.CREATED",
                     entity_type="api_key", entity_id=key.id,
                     after={"institution_id": institution_id, "name": name, "prefix": key.prefix})
    return key, token


def list_keys(db: Session, institution_id: str) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.institution_id == institution_id)
                           .order_by(ApiKey.created_at.desc(), ApiKey.id)))


def revoke(db: Session, actor: User, key: ApiKey) -> ApiKey:
    with uow(db):
        if key.revoked_at is None:
            key.revoked_at = clock.now()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="APIKEY.REVOKED",
                     entity_type="api_key", entity_id=key.id,
                     after={"institution_id": key.institution_id, "prefix": key.prefix})
    return key


def find(db: Session, token: str) -> ApiKey | None:
    return db.scalars(select(ApiKey).where(ApiKey.key_hash == _hash(token))).first()


def record_use(db: Session, key: ApiKey, action: str = "APIKEY.USED", **after) -> None:
    with uow(db):
        if action == "APIKEY.USED":
            key.last_used_at = clock.now()
        audit.append(db, actor_id=None, actor_role="API_KEY", action=action,
                     entity_type="api_key", entity_id=key.id,
                     after={"institution_id": key.institution_id, "prefix": key.prefix, **after})
