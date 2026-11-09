"""Consent ledger, verifier registration and approval, purpose policies."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.models.audit import AuditLog
from app.models.consent import Consent, PurposePolicy, Verifier
from app.models.user import User
from tests.ingest_helpers import ap
from tests.phase6_helpers import ask, give, scene

C = "/api/v1/consents"


@pytest.fixture
def s(db, world):
    return scene(db, world)


def body(apaar, **kw):
    exp = (clock.now() + timedelta(days=90)).isoformat()
    return {"apaar_id": apaar, "purposes": ["EMPLOYMENT"], "fields": ["name", "programme"],
            "source": "INSTITUTION_PORTAL", "expires_at": exp} | kw


def actions(db):
    return [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]


# --- consents ----------------------------------------------------------------------------

def test_institution_records_consent_for_its_own_student(client, db, login, s, world):
    r = client.post(C, headers=login("kaveri.staff@demo.test"), json=body(ap(2)))
    assert r.status_code == 201, r.text
    c = db.get(Consent, r.json()["id"])
    assert c.recorded_by == world["users"]["inst_staff"].id and c.withdrawn_at is None
    assert c.given_at is not None and "CONSENT.RECORDED" in actions(db)
    # the new consent works for a verification
    vh = login("verifier@demo.test")
    assert ask(client, vh, ap(2), fields=("name", "programme")).json()["outcome"] == "GRANTED"


def test_institution_cannot_record_consent_for_another_institutions_student(
        client, db, login, s):
    r = client.post(C, headers=login("kaveri.admin@demo.test"), json=body(ap(5)))
    assert r.status_code == 403
    assert "ACCESS.REFUSED" in actions(db)
    assert db.scalars(select(Consent).where(Consent.apaar_id == ap(5))).first() is None


def test_unknown_student_looks_the_same_to_an_institution(client, login, s):
    r = client.post(C, headers=login("kaveri.admin@demo.test"), json=body("999999999999"))
    assert r.status_code == 403


def test_admin_can_record_for_any_student_but_not_an_unknown_one(client, login, s):
    h = login("admin@demo.test")
    assert client.post(C, headers=h, json=body(ap(5))).status_code == 201
    assert client.post(C, headers=h, json=body("999999999999")).status_code == 404


def test_roles_that_may_not_record(client, login, s):
    for who in ("officer.south@demo.test", "verifier@demo.test"):
        assert client.post(C, headers=login(who), json=body(ap(1))).status_code == 403
    assert client.post(C, json=body(ap(1))).status_code == 401


@pytest.mark.parametrize("extra", [{"recorded_by": "x"}, {"withdrawn_at": "2020-01-01T00:00:00Z"},
                                   {"given_at": "2020-01-01T00:00:00Z"}, {"id": "x"}])
def test_mass_assignment_is_refused(client, login, s, extra):
    r = client.post(C, headers=login("admin@demo.test"), json=body(ap(1)) | extra)
    assert r.status_code == 422


def test_validation(client, login, s):
    h = login("admin@demo.test")
    past = (clock.now() - timedelta(days=1)).isoformat()
    assert client.post(C, headers=h, json=body(ap(1), expires_at=past)).status_code == 422
    assert client.post(C, headers=h, json=body(ap(1), purposes=[])).status_code == 422
    assert client.post(C, headers=h, json=body(ap(1), purposes=["X"])).status_code == 422
    assert client.post(C, headers=h, json=body(ap(1), fields=["dob"])).status_code == 422
    assert client.post(C, headers=h, json=body(ap(1), fields=[])).status_code == 422
    assert client.post(C, headers=h, json=body(ap(1), expires_at="2999-01-01T00:00:00Z")
                       ).status_code == 422  # absurdly far: capped


def test_withdraw_blocks_verification_and_is_scoped(client, db, login, s):
    cid = db.scalars(select(Consent)).one().id
    assert client.delete(f"{C}/{cid}", headers=login("verifier@demo.test")).status_code == 403
    assert client.delete(f"{C}/nope", headers=login("admin@demo.test")).status_code == 404
    assert client.delete(f"{C}/{cid}", headers=login("kaveri.staff@demo.test")).status_code == 200
    assert db.get(Consent, cid).withdrawn_at is not None and "CONSENT.WITHDRAWN" in actions(db)
    assert client.delete(f"{C}/{cid}", headers=login("admin@demo.test")).status_code == 409
    r = ask(client, login("verifier@demo.test"), ap(1))
    assert r.json()["outcome"] == "REFUSED"


def test_other_institution_cannot_withdraw(client, db, login, s, world):
    from tests.phase5_helpers import add_user
    add_user(db, "north.admin@demo.test", "INSTITUTION_ADMIN", world["northfield"])
    cid = db.scalars(select(Consent)).one().id
    assert client.delete(f"{C}/{cid}", headers=login("north.admin@demo.test")).status_code == 403
    assert "ACCESS.REFUSED" in actions(db)
    assert db.get(Consent, cid).withdrawn_at is None


def test_list_is_scoped_and_masked(client, db, login, s, world):
    from tests.phase5_helpers import add_user
    give(db, ap(5))
    add_user(db, "north.admin@demo.test", "INSTITUTION_ADMIN", world["northfield"])
    k = client.get(C, headers=login("kaveri.admin@demo.test")).json()["items"]
    assert [c["apaar_id"] for c in k] == [ap(1)]
    n = client.get(C, headers=login("north.admin@demo.test")).json()["items"]
    assert [c["apaar_id"] for c in n] == [ap(5)]
    assert len(client.get(C, headers=login("admin@demo.test")).json()["items"]) == 2
    south = client.get(C, headers=login("officer.south@demo.test")).json()["items"]
    assert [c["apaar_id"] for c in south] == [ap(1)]  # Northfield is North
    # filtering by an ID outside scope returns nothing, not an error that confirms it exists
    r = client.get(C, headers=login("kaveri.admin@demo.test"), params={"apaar": ap(5)})
    assert r.status_code == 200 and r.json()["items"] == []
    assert client.get(C, headers=login("verifier@demo.test")).status_code == 403
    assert "recorded_by" not in k[0]


# --- verifier registration ---------------------------------------------------------------

REG = {"org_name": "Fictional Hiring Ltd", "org_type": "EMPLOYER", "contact": "Asha Rao",
       "email": "hiring@fictional.test", "password": "Correct-Horse-9",
       "requested_purposes": ["EMPLOYMENT"]}
R = "/api/v1/verifiers/register"


def test_register_creates_inactive_user_and_pending_verifier(client, db):
    r = client.post(R, json=REG)
    assert r.status_code == 202, r.text
    u = db.scalars(select(User).where(User.email == REG["email"])).one()
    assert u.role == "VERIFIER" and not u.is_active and u.password_hash != REG["password"]
    v = db.scalars(select(Verifier).where(Verifier.user_id == u.id)).one()
    assert v.status == "PENDING"
    login = client.post("/api/v1/auth/login", json={"email": REG["email"],
                                                    "password": REG["password"]})
    assert login.status_code == 401  # cannot sign in before approval
    assert "VERIFIER.REGISTERED" in actions(db)


def test_register_does_not_reveal_whether_the_email_exists(client, db, s):
    first = client.post(R, json=REG)
    again = client.post(R, json=REG)
    existing = client.post(R, json=REG | {"email": "admin@demo.test"})
    assert first.status_code == again.status_code == existing.status_code == 202
    assert first.json() == again.json() == existing.json()
    assert len(db.scalars(select(Verifier).where(Verifier.org_name == REG["org_name"])).all()) == 1
    assert db.scalars(select(User).where(User.email == "admin@demo.test")).one().role == "AICTE_ADMIN"


@pytest.mark.parametrize("bad", [{"password": "short"}, {"password": "x" * 80},
                                 {"org_type": "ROBOT"}, {"requested_purposes": []},
                                 {"role": "AICTE_ADMIN"}, {"status": "APPROVED"},
                                 {"is_active": True}, {"email": "not-an-email"}])
def test_register_validation_and_mass_assignment(client, db, bad):
    assert client.post(R, json=REG | bad).status_code == 422
    assert db.scalars(select(Verifier)).first() is None


def test_register_is_rate_limited(client):
    from app.core.config import settings
    old = settings.register_max_per_hour
    settings.register_max_per_hour = 2
    try:
        codes = [client.post(R, json=REG | {"email": f"v{i}@fictional.test"}).status_code
                 for i in range(4)]
    finally:
        settings.register_max_per_hour = old
    assert codes == [202, 202, 429, 429]


def pending(client, db):
    client.post(R, json=REG)
    return db.scalars(select(Verifier).where(Verifier.org_name == REG["org_name"])).one()


def test_approve_requires_a_note_and_activates_the_user(client, db, login):
    v = pending(client, db)
    admin = login("admin@demo.test")
    url = f"/api/v1/admin/verifiers/{v.id}/approve"
    assert client.post(url, headers=admin, json={"note": " "}).status_code == 422
    assert client.post(url, headers=admin, json={}).status_code == 422
    assert client.post(url, headers=admin, json={"note": "Checked registration"}).status_code == 200
    assert db.get(Verifier, v.id).status == "APPROVED"
    assert db.get(Verifier, v.id).decision_note == "Checked registration"
    assert "VERIFIER.APPROVED" in actions(db)
    assert client.post("/api/v1/auth/login", json={"email": REG["email"],
                                                   "password": REG["password"]}).status_code == 200
    assert client.post(url, headers=admin, json={"note": "again"}).status_code == 409
    rej = client.post(f"/api/v1/admin/verifiers/{v.id}/reject", headers=admin,
                      json={"note": "late"})
    assert rej.status_code == 409


def test_reject_keeps_the_user_inactive(client, db, login):
    v = pending(client, db)
    r = client.post(f"/api/v1/admin/verifiers/{v.id}/reject", headers=login("admin@demo.test"),
                    json={"note": "Not an AICTE stakeholder"})
    assert r.status_code == 200 and db.get(Verifier, v.id).status == "REJECTED"
    assert client.post("/api/v1/auth/login", json={"email": REG["email"],
                                                   "password": REG["password"]}).status_code == 401


def test_only_admin_decides_and_lists_verifiers(client, db, login):
    v = pending(client, db)
    for who in ("officer.south@demo.test", "kaveri.admin@demo.test", "verifier@demo.test"):
        h = login(who)
        assert client.post(f"/api/v1/admin/verifiers/{v.id}/approve", headers=h,
                           json={"note": "x"}).status_code == 403
        assert client.get("/api/v1/admin/verifiers", headers=h).status_code == 403
    items = client.get("/api/v1/admin/verifiers", headers=login("admin@demo.test"),
                       params={"status": "PENDING"}).json()["items"]
    assert [i["org_name"] for i in items] == [REG["org_name"]]
    assert "password_hash" not in items[0]
    assert client.post("/api/v1/admin/verifiers/nope/approve", headers=login("admin@demo.test"),
                       json={"note": "x"}).status_code == 404


# --- purpose policies --------------------------------------------------------------------

P = "/api/v1/admin/policies"


def test_policy_put_creates_a_new_version_and_applies_at_once(client, db, login, s):
    admin = login("admin@demo.test")
    got = {p["purpose"]: p for p in client.get(P, headers=admin).json()["items"]}
    assert set(got) == {"EMPLOYMENT", "HIGHER_EDUCATION", "REGULATORY", "SCHOLARSHIP"}
    assert got["EMPLOYMENT"]["allowed_fields"] == ["name", "programme", "status"]
    assert client.put(f"{P}/EMPLOYMENT", headers=admin,
                      json={"allowed_fields": ["name"], "note": ""}).status_code == 422
    r = client.put(f"{P}/EMPLOYMENT", headers=admin,
                   json={"allowed_fields": ["name"], "note": "Minimise"})
    assert r.status_code == 200 and r.json()["version"] == 2
    rows = db.scalars(select(PurposePolicy).where(PurposePolicy.purpose == "EMPLOYMENT")
                      .order_by(PurposePolicy.version)).all()
    assert [(p.version, p.is_active) for p in rows] == [(1, False), (2, True)]
    assert "POLICY.UPDATED" in actions(db)
    refused = ask(client, login("verifier@demo.test"), ap(1))
    assert refused.json()["reason"] == "FIELD_NOT_ALLOWED_BY_POLICY"
    assert refused.json()["detail"] == ["programme", "status"]


def test_policy_validation_and_access(client, login, s):
    admin = login("admin@demo.test")
    ok = {"allowed_fields": ["name"], "note": "n"}
    assert client.put(f"{P}/EMPLOYMENT", headers=admin,
                      json={**ok, "allowed_fields": ["dob"]}).status_code == 422
    assert client.put(f"{P}/GOSSIP", headers=admin, json=ok).status_code == 422
    assert client.put(f"{P}/EMPLOYMENT", headers=admin, json={**ok, "version": 9}).status_code == 422
    for who in ("officer.south@demo.test", "kaveri.admin@demo.test", "verifier@demo.test"):
        h = login(who)
        assert client.put(f"{P}/EMPLOYMENT", headers=h, json=ok).status_code == 403
        assert client.get(P, headers=h).status_code == 403


def test_register_hashes_the_password_even_when_the_email_exists(client, monkeypatch):
    """No timing difference between a new and an existing email."""
    from app.services import verifiers as svc
    calls = []
    real = svc.hash_password
    monkeypatch.setattr(svc, "hash_password", lambda p: calls.append(1) or real(p))
    client.post(R, json=REG)
    client.post(R, json=REG)
    assert len(calls) == 2
