"""Hash-chained audit log. Tamper evident, not tamper proof."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.audit import AuditLog

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


def verify(db: Session) -> dict:
    """Walk the chain. Report the first row whose link or content does not match."""
    prev, count = GENESIS, 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        count += 1
        if row.prev_hash != prev or row.hash != _digest(prev, row):
            return {"ok": False, "count": count, "first_broken_id": row.id}
        prev = row.hash
    return {"ok": True, "count": count, "first_broken_id": None}
