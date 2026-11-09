import pytest
from sqlalchemy import select

from app.core import clock
from app.models.audit import AuditLog
from app.services import audit


@pytest.fixture(autouse=True)
def _reset_clock():
    clock.set_offset(0)
    yield
    clock.set_offset(0)


def names(r):
    return sorted(i["name"] for i in r.json())


def test_admin_sees_every_institution(client, login):
    r = client.get("/api/v1/institutions", headers=login("admin@demo.test"))
    assert len(r.json()) == 3


def test_officer_sees_only_assigned_regions(client, login):
    r = client.get("/api/v1/institutions", headers=login("officer.south@demo.test"))
    assert names(r) == ["Kaveri Valley College", "Malabar Pharmacy College"]


def test_institution_user_sees_only_their_own(client, login):
    r = client.get("/api/v1/institutions", headers=login("kaveri.admin@demo.test"))
    assert names(r) == ["Kaveri Valley College"]


def test_missing_institution_is_404_for_admin(client, login):
    r = client.get("/api/v1/institutions/nope", headers=login("admin@demo.test"))
    assert r.status_code == 404


def test_cross_institution_read_is_refused_and_logged(client, login, db, world):
    h = login("kaveri.admin@demo.test")
    r = client.get(f"/api/v1/institutions/{world['malabar'].id}", headers=h)
    assert r.status_code == 403
    refusal = db.scalars(select(AuditLog).where(AuditLog.action == "ACCESS.REFUSED")).all()
    assert len(refusal) == 1 and refusal[0].entity_id == world["malabar"].id
    assert audit.verify(db)["ok"] is True


def test_audit_verify_endpoint_reports_ok(client, login):
    r = client.post("/api/v1/admin/audit/verify", headers=login("admin@demo.test"))
    assert r.status_code == 200 and r.json()["ok"] is True


def test_clock_advance_and_reset_are_audited(client, login, db):
    h = login("admin@demo.test")
    r = client.post("/api/v1/admin/clock", json={"advance_days": 2}, headers=h)
    assert r.status_code == 200
    assert clock.get_offset_seconds() == pytest.approx(2 * 86400)
    assert client.get("/api/v1/admin/clock", headers=h).json()["offset_days"] == 2
    client.post("/api/v1/admin/clock", json={"reset": True}, headers=h)
    assert clock.get_offset_seconds() == 0
    actions = db.scalars(select(AuditLog.action).where(AuditLog.action == "CLOCK.SET")).all()
    assert len(actions) == 2


def test_clock_rejects_empty_or_unknown_body(client, login):
    h = login("admin@demo.test")
    assert client.post("/api/v1/admin/clock", json={}, headers=h).status_code == 422
    assert client.post("/api/v1/admin/clock", json={"days": 1}, headers=h).status_code == 422


def test_audit_list_is_paginated(client, login):
    h = login("admin@demo.test")
    r = client.get("/api/v1/admin/audit?limit=1", headers=h)
    assert r.status_code == 200 and len(r.json()["items"]) <= 1
