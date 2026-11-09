import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.models.audit import AuditLog
from app.services import audit


def _write(db, n=3):
    for i in range(n):
        audit.append(
            db, actor_id="u1", actor_role="AICTE_ADMIN", action="TEST.WRITE",
            entity_type="thing", entity_id=str(i), before=None, after={"n": i},
        )
    db.commit()


def test_clean_chain_verifies(db):
    _write(db)
    assert audit.verify(db) == {"ok": True, "count": 3, "first_broken_id": None}


def test_empty_chain_is_ok(db):
    assert audit.verify(db)["ok"] is True


def test_edited_row_is_found(db):
    _write(db)
    db.execute(update(AuditLog).where(AuditLog.id == 2).values(after={"n": 999}))
    db.commit()
    r = audit.verify(db)
    assert r["ok"] is False and r["first_broken_id"] == 2


def test_deleted_middle_row_is_found(db):
    _write(db)
    db.execute(delete(AuditLog).where(AuditLog.id == 2))
    db.commit()
    r = audit.verify(db)
    assert r["ok"] is False and r["first_broken_id"] == 3


def test_deleted_first_row_is_found(db):
    _write(db)
    db.execute(delete(AuditLog).where(AuditLog.id == 1))
    db.commit()
    r = audit.verify(db)
    assert r["ok"] is False and r["first_broken_id"] == 2


def test_two_entries_with_same_predecessor_are_rejected_by_db(db):
    _write(db, 1)
    first = db.get(AuditLog, 1)
    db.add(AuditLog(
        occurred_at=first.occurred_at, actor_id="x", actor_role="r", action="FORK",
        entity_type="t", entity_id="1", prev_hash=first.prev_hash, hash="f" * 64,
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_entries_chain_from_genesis(db):
    _write(db, 1)
    assert db.get(AuditLog, 1).prev_hash == audit.GENESIS
