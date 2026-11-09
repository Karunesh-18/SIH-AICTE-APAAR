"""Hash-chained audit log. Tamper evident, not tamper proof."""
import hashlib
import json

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import settings
from app.db.session import uow
from app.models.audit import AuditCheckpoint, AuditLog
from app.services import signing
from app.services.errors import Invalid

GENESIS = "0" * 64


def _canonical(row: AuditLog) -> str:
    return json.dumps(
        {
            "id": row.id,
            "occurred_at": row.occurred_at.isoformat(),
            "actor_id": row.actor_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "before": row.before,
            "after": row.after,
        },
        sort_keys=True,
        default=str,
    )


def _digest(prev_hash: str, row: AuditLog) -> str:
    return hashlib.sha256((prev_hash + _canonical(row)).encode()).hexdigest()


def append(
    db: Session, *, actor_id, actor_role, action, entity_type, entity_id,
    before=None, after=None,
) -> AuditLog:
    """Runs inside the caller's transaction so the audit entry commits with the change."""
    last = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).first()
    row = AuditLog(
        occurred_at=clock.now(), actor_id=actor_id, actor_role=actor_role, action=action,
        entity_type=entity_type, entity_id=str(entity_id), before=before, after=after,
        prev_hash=last.hash if last else GENESIS, hash="",
    )
    db.add(row)
    db.flush()  # assigns id, which is part of the hashed content
    row.hash = _digest(row.prev_hash, row)
    db.flush()
    return row


def _chain_ok(db: Session, upto: int | None = None) -> dict:
    """Walk the chain. Report the first row whose link or content does not match."""
    prev, count = GENESIS, 0
    q = select(AuditLog).order_by(AuditLog.id)
    for row in db.scalars(q.where(AuditLog.id <= upto) if upto else q):
        count += 1
        if row.prev_hash != prev or row.hash != _digest(prev, row):
            return {"ok": False, "count": count, "first_broken_id": row.id}
        prev = row.hash
    return {"ok": True, "count": count, "first_broken_id": None}


def verify(db: Session) -> dict:
    out = _chain_ok(db)
    last = db.scalars(select(AuditCheckpoint).order_by(AuditCheckpoint.id.desc()).limit(1)).first()
    out["checkpoint"] = verify_against(db, last.token) if last else None
    return out


# ---- signed checkpoints: catch truncation of the last rows, which the chain alone cannot see ----

CHECKPOINT_REQUIRED = ["typ", "seq", "hash", "count", "iat", "iss"]


def create_checkpoint(db: Session, actor=None) -> AuditCheckpoint:
    """Sign the chain head. No expiry: a checkpoint is evidence and stays valid."""
    head = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).first()
    if head is None:
        raise Invalid("The audit log is empty, so there is nothing to checkpoint")
    now = clock.now()
    count = db.scalar(select(func.count()).select_from(AuditLog))
    claims = {"typ": "AUDIT_CHECKPOINT", "seq": head.id, "hash": head.hash, "count": count,
              "iat": int(now.timestamp()), "iss": settings.verify_issuer}
    with uow(db):
        cp = AuditCheckpoint(seq=head.id, hash=head.hash, count=count, signed_at=now,
                             token=signing.sign(claims))
        db.add(cp)
        db.flush()
        append(db, actor_id=actor.id if actor else None,
               actor_role=actor.role if actor else "SYSTEM", action="AUDIT.CHECKPOINT",
               entity_type="audit_checkpoint", entity_id=cp.id,
               after={"seq": cp.seq, "count": count})
    return cp


def verify_against(db: Session, token: str) -> dict:
    """ok, or the reason: bad_signature, missing_rows (head row gone: truncation), hash_mismatch."""
    try:
        claims = signing.verify(token, CHECKPOINT_REQUIRED)
        if claims["typ"] != "AUDIT_CHECKPOINT":
            raise jwt.InvalidTokenError("wrong type")
    except jwt.PyJWTError:
        return {"ok": False, "reason": "bad_signature"}
    head = db.get(AuditLog, claims["seq"])
    if head is None:
        return {"ok": False, "reason": "missing_rows"}
    if head.hash != claims["hash"] or not _chain_ok(db, claims["seq"])["ok"]:
        return {"ok": False, "reason": "hash_mismatch"}
    return {"ok": True, "reason": None}


def checkpoint_out(cp: AuditCheckpoint) -> dict:
    return {"seq": cp.seq, "hash": cp.hash, "count": cp.count, "signed_at": cp.signed_at,
            "token": cp.token}
