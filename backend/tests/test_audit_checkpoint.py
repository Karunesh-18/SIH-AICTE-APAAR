import pytest

from app.core.config import settings
from app.models.audit import AuditLog
from app.services import audit, signing
from app.services.errors import Invalid

A = "/api/v1/admin"


def _seed(db, n=3):
    for i in range(n):
        audit.append(db, actor_id=None, actor_role="SYSTEM", action="T", entity_type="t",
                     entity_id=str(i))
    db.commit()


def test_checkpoint_is_signed_and_verifies(client, login, db):
    _seed(db)
    r = client.post(f"{A}/audit/checkpoint", headers=login("admin@demo.test"))
    assert r.status_code == 200
    cp = r.json()
    assert cp["seq"] == cp["count"] >= 3
    claims = signing.verify(cp["token"], audit.CHECKPOINT_REQUIRED)
    assert claims["typ"] == "AUDIT_CHECKPOINT" and claims["hash"] == cp["hash"]
    assert audit.verify(db)["checkpoint"] == {"ok": True, "reason": None}


def test_public_list_without_auth_and_verify(client, login, db):
    _seed(db)
    token = client.post(f"{A}/audit/checkpoint", headers=login("admin@demo.test")).json()["token"]
    lst = client.get("/api/v1/audit/checkpoints")
    assert lst.status_code == 200 and lst.json()[0]["token"] == token
    r = client.post("/api/v1/audit/checkpoints/verify", json={"token": token})
    assert r.json() == {"ok": True, "reason": None}
    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert last.action == "AUDIT.CHECKPOINT_CHECKED"


def test_truncation_is_caught_though_the_chain_still_verifies(client, login, db):
    _seed(db)
    h = login("admin@demo.test")
    client.post(f"{A}/audit/checkpoint", headers=h)
    assert client.post(f"{A}/dev/truncate-audit?n=2", headers=h).json() == {"deleted": 2}
    v = client.post(f"{A}/audit/verify", headers=h).json()
    assert v["ok"] is True
    assert v["checkpoint"] == {"ok": False, "reason": "missing_rows"}


def test_editing_the_checkpointed_row_is_hash_mismatch(client, login, db):
    _seed(db)
    seq = client.post(f"{A}/audit/checkpoint", headers=login("admin@demo.test")).json()["seq"]
    db.get(AuditLog, seq).after = {"tampered": True}
    db.commit()
    assert audit.verify(db)["checkpoint"] == {"ok": False, "reason": "hash_mismatch"}


def test_altered_token_is_bad_signature(client, login, db):
    _seed(db)
    t = client.post(f"{A}/audit/checkpoint", headers=login("admin@demo.test")).json()["token"]
    bad = t[:-1] + ("A" if t[-1] != "A" else "B")
    assert audit.verify_against(db, bad) == {"ok": False, "reason": "bad_signature"}


def test_empty_log_refuses(db):
    with pytest.raises(Invalid):
        audit.create_checkpoint(db, None)


def test_truncate_is_off_outside_demo_mode(client, login, monkeypatch):
    h = login("admin@demo.test")
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.post(f"{A}/dev/truncate-audit", headers=h).status_code == 404
