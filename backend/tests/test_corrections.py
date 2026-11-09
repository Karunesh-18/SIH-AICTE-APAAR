"""Phase 4: record corrections (new version, re-validation), withdrawal, pending-APAAR flow."""
import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.notify import Notification
from app.models.student import FlagEvent, StudentRecord, ValidationFlag
from app.models.user import User, UserRegion
from tests.conftest import PASSWORD
from tests.ingest_helpers import ap, csv_bytes, programme, register, row, run


@pytest.fixture
def scene(db, world, rules):
    """Kaveri: row 1 clean, row 2 has an 11-digit ID (R02), row 3 has no ID (R01)."""
    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    programme(db, world["malabar"], name="B.Pharm")
    rows = [row(1), row(2, apaar_id="99990000002"), row(3, apaar_id="")]
    register(db, [row(1), row(2), row(3)])
    run(db, world["kaveri"], csv_bytes(rows))
    for email, role, inst in (("malabar.admin@demo.test", "INSTITUTION_ADMIN", "malabar"),
                              ("northfield.staff@demo.test", "INSTITUTION_STAFF", "northfield")):
        db.add(User(email=email, password_hash=hash_password(PASSWORD), full_name=email,
                    role=role, institution_id=world[inst].id))
    north = User(email="officer.north@demo.test", password_hash=hash_password(PASSWORD),
                 full_name="North", role="AICTE_OFFICER")
    db.add(north)
    db.flush()
    db.add(UserRegion(user_id=north.id, region_id=world["north"].id))
    db.commit()


def rec(db, n, current=True):
    return db.scalars(select(StudentRecord).where(
        StudentRecord.row_number == n, StudentRecord.is_current == current)).first()


def patch(client, h, rid, **body):
    return client.patch(f"/api/v1/records/{rid}", headers=h, json=body)


def flags_on(db, record_id):
    from app.models.student import FlagRecord
    return db.scalars(select(ValidationFlag).join(
        FlagRecord, FlagRecord.flag_id == ValidationFlag.id).where(
        FlagRecord.record_id == record_id)).all()


def test_correction_creates_version_two_and_closes_the_stale_flag(client, login, db, scene):
    old = rec(db, 2)
    r = patch(client, login("kaveri.staff@demo.test"), old.id, apaar_id="999900000002")
    assert r.status_code == 200, r.text
    out = r.json()
    new, prev = out["record"], out["previous"]
    assert (new["version"], new["is_current"], new["apaar_id"]) == (2, True, "999900000002")
    assert (prev["version"], prev["is_current"], prev["apaar_id"]) == (1, False, "99990000002")
    assert new["status"] == "valid"
    db.expire_all()
    old = db.get(StudentRecord, old.id)
    nrec = db.get(StudentRecord, new["id"])
    assert old.superseded_by == nrec.id and old.superseded_at is not None
    assert nrec.continues_record_id == old.id and nrec.name == old.name
    (stale,) = [f for f in flags_on(db, old.id) if f.rule_code == "R02"]
    assert stale.state == "resolved"
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == stale.id)
                    .order_by(FlagEvent.at)).all()[-1]
    assert ev.note == "superseded by correction" and ev.actor_id is None
    assert [f["rule_code"] for f in out["closed_flags"]] == ["R02"] and out["raised_flags"] == []
    versions = client.get(f"/api/v1/records/{nrec.id}", headers=login("kaveri.staff@demo.test")
                          ).json()["versions"]
    assert [v["version"] for v in versions] == [1, 2]


def test_correction_can_raise_a_new_flag(client, login, db, scene):
    old = rec(db, 1)
    r = patch(client, login("kaveri.admin@demo.test"), old.id, admission_date="2031-02-03")
    out = r.json()
    assert out["record"]["status"] == "flagged"
    assert [f["rule_code"] for f in out["raised_flags"]] == ["R07"]
    (f,) = [f for f in flags_on(db, out["record"]["id"]) if f.rule_code == "R07"]
    assert f.state == "open" and "2031-02-03" in str(f.evidence)


def test_correction_is_audited_with_before_and_after(client, login, db, scene):
    old = rec(db, 1)
    patch(client, login("admin@demo.test"), old.id, name="Corrected Name")
    a = db.scalars(select(AuditLog).where(AuditLog.action == "RECORD.CORRECTED")).one()
    assert a.before == {"name": "Student 1"} and a.after["name"] == "Corrected Name"
    assert a.entity_id == old.id


def test_who_may_correct(client, login, db, world, scene):
    old = rec(db, 1)
    for who in ("officer.south@demo.test", "verifier@demo.test"):
        assert patch(client, login(who), old.id, name="X").status_code == 403
    assert patch(client, login("malabar.admin@demo.test"), old.id, name="X").status_code == 403
    assert db.scalars(select(AuditLog).where(AuditLog.action == "ACCESS.REFUSED")).first()
    assert rec(db, 1).version == 1
    assert patch(client, login("admin@demo.test"), old.id, name="Admin Fix").status_code == 200


def test_bad_bodies_and_stale_targets(client, login, db, scene):
    h = login("kaveri.admin@demo.test")
    old = rec(db, 1)
    assert patch(client, h, old.id).status_code == 422                       # nothing to change
    assert patch(client, h, old.id, programme="MBA").status_code == 422      # not editable
    assert patch(client, h, "missing", name="X").status_code == 404
    assert patch(client, h, old.id, name="Second").status_code == 200
    assert patch(client, h, old.id, name="Stale").status_code == 409         # old version


def test_correcting_into_an_id_already_current_in_the_programme_is_409(client, login, db, scene):
    r = patch(client, login("kaveri.admin@demo.test"), rec(db, 2).id, apaar_id=ap(1))
    assert r.status_code == 409 and "already" in r.json()["detail"]
    assert rec(db, 2).version == 1


def test_pending_apaar_gets_its_id_and_the_r01_flag_is_closed_by_the_system(
        client, login, db, scene):
    old = rec(db, 3)
    assert old.status == "pending_apaar"
    out = patch(client, login("kaveri.staff@demo.test"), old.id, apaar_id="9999 0000 0003").json()
    assert out["record"]["apaar_id"] == ap(3) and out["record"]["status"] == "valid"
    (r01,) = [f for f in flags_on(db, old.id) if f.rule_code == "R01"]
    db.refresh(r01)
    assert r01.state == "resolved"
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == r01.id)
                    .order_by(FlagEvent.at)).all()[-1]
    assert ev.actor_id is None and "APAAR ID" in ev.note and "R01" in ev.note


def test_pending_apaar_with_a_bad_id_moves_to_flagged_with_r02(client, login, db, scene):
    old = rec(db, 3)
    out = patch(client, login("kaveri.staff@demo.test"), old.id, apaar_id="12345").json()
    assert out["record"]["status"] == "flagged"
    assert [f["rule_code"] for f in out["raised_flags"]] == ["R02"]
    assert [f["rule_code"] for f in out["closed_flags"]] == ["R01"]


def test_pending_apaar_unknown_to_the_registry_raises_r03(client, login, db, scene):
    out = patch(client, login("kaveri.staff@demo.test"), rec(db, 3).id,
                apaar_id="999900009999").json()
    assert [f["rule_code"] for f in out["raised_flags"]] == ["R03"]


# ---- withdraw ----------------------------------------------------------------------------------

def wd(client, h, rid, **body):
    return client.post(f"/api/v1/records/{rid}/withdraw", headers=h, json=body)


def test_withdraw_needs_a_reason_and_keeps_the_record_current(client, login, db, scene):
    h = login("kaveri.admin@demo.test")
    old = rec(db, 1)
    assert wd(client, h, old.id).status_code == 422
    assert wd(client, h, old.id, reason="  ").status_code == 422
    r = wd(client, h, old.id, reason="Transferred to another college")
    assert r.status_code == 200 and r.json()["status"] == "withdrawn"
    db.expire_all()
    got = db.get(StudentRecord, old.id)
    assert got.is_current and got.status == "withdrawn"
    assert got.withdrawn_reason == "Transferred to another college" and got.version == 1
    a = db.scalars(select(AuditLog).where(AuditLog.action == "RECORD.WITHDRAWN")).one()
    assert a.before == {"status": "valid"} and a.after["reason"].startswith("Transferred")
    assert wd(client, h, old.id, reason="again").status_code == 409
    assert patch(client, h, old.id, name="X").status_code == 409


def test_who_may_withdraw(client, login, db, scene):
    old = rec(db, 1)
    for who in ("officer.south@demo.test", "verifier@demo.test", "malabar.admin@demo.test"):
        assert wd(client, login(who), old.id, reason="x").status_code == 403
    assert rec(db, 1).status == "valid"


def test_demo_case_four_withdraw_then_officer_resolves_nobody_blocked(
        client, login, db, world, scene):
    kaveri_rec = rec(db, 1)  # Kaveri lists ap(1); Northfield then lists the same student
    up = run(db, world["northfield"], csv_bytes([row(1)]))
    assert up.status == "DONE"
    (r05,) = db.scalars(select(ValidationFlag).where(ValidationFlag.rule_code == "R05")).all()
    assert r05.institution_id == world["northfield"].id and r05.state == "open"

    assert wd(client, login("kaveri.admin@demo.test"), kaveri_rec.id,
              reason="Student moved to Northfield mid-year").status_code == 200
    told = db.scalars(select(Notification).where(
        Notification.channel == "IN_APP",
        Notification.user_id.in_(select(User.id).where(
            User.email.in_(["northfield.staff@demo.test", "officer.north@demo.test"]))))).all()
    assert {n.related_id for n in told} >= {r05.id}  # counterpart and region officer are told
    db.refresh(r05)
    assert r05.state == "open"  # the officer decides, not the system

    r = client.post(f"/api/v1/flags/{r05.id}/resolve", headers=login("officer.north@demo.test"),
                    json={"note": "Kaveri withdrew; Northfield is the active institution."})
    assert r.status_code == 200 and r.json()["state"] == "resolved"
    # nobody was blocked: both records stored, and the withdrawn one no longer triggers R05
    assert db.get(StudentRecord, kaveri_rec.id).is_current
    run(db, world["malabar"], csv_bytes([row(1)]))
    later = [f for f in db.scalars(select(ValidationFlag).where(
        ValidationFlag.institution_id == world["malabar"].id, ValidationFlag.rule_code == "R05"))]
    assert len(later) == 1
    names = [e["institution"] for e in later[0].evidence["elsewhere"]]
    assert names == ["Northfield Institute"]
