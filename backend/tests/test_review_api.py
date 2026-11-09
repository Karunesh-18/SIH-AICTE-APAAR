"""Phase 4 review queue: scoping, state machine over HTTP, notes, locking, audit, notifications."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.notify import Notification
from app.models.student import FlagEvent, ValidationFlag
from app.models.user import User
from tests.conftest import PASSWORD
from tests.ingest_helpers import csv_bytes, programme, register, row, run

B = "/api/v1/flags"


@pytest.fixture
def scene(db, world, rules):
    """Kaveri (south): R02 on row 2, R01 on row 3. Northfield (north): R03 on row 1."""
    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    rows = [row(1), row(2, apaar_id="99990000002"), row(3, apaar_id="")]
    register(db, rows)
    run(db, world["kaveri"], csv_bytes(rows))
    run(db, world["northfield"], csv_bytes([row(50)]))
    mal = User(email="malabar.admin@demo.test", password_hash=hash_password(PASSWORD),
               full_name="m", role="INSTITUTION_ADMIN", institution_id=world["malabar"].id)
    db.add(mal)
    db.commit()


def flag(db, inst, rule):
    return db.scalars(select(ValidationFlag).where(ValidationFlag.institution_id == inst.id,
                                                   ValidationFlag.rule_code == rule)).first()


def act(client, h, fid, action, note="looked at it", **kw):
    body = ({"note": note} if note is not None else {}) | kw
    return client.post(f"{B}/{fid}/{action}", headers=h, json=body)


def audit_actions(db):
    return [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]


# ---- list --------------------------------------------------------------------------------------

def test_list_scope_by_role(client, login, db, world, scene):
    admin, officer = login("admin@demo.test"), login("officer.south@demo.test")
    kav, mal = login("kaveri.admin@demo.test"), login("malabar.admin@demo.test")
    a = client.get(B, headers=admin).json()
    assert a["total"] == 3 and {i["institution_id"] for i in a["items"]} == {
        world["kaveri"].id, world["northfield"].id}
    o = client.get(B, headers=officer).json()
    assert o["total"] == 2 and {i["institution_id"] for i in o["items"]} == {world["kaveri"].id}
    assert client.get(B, headers=kav).json()["total"] == 2
    assert client.get(B, headers=mal).json() == {"items": [], "total": 0}
    assert client.get(B, headers=login("verifier@demo.test")).status_code == 403


def test_list_filters_and_pagination(client, login, db, world, scene):
    h = login("admin@demo.test")
    assert client.get(B, headers=h, params={"rule": "R02"}).json()["total"] == 1
    assert client.get(B, headers=h, params={"state": "resolved"}).json()["total"] == 0
    assert client.get(B, headers=h, params={"institution": world["northfield"].id}
                      ).json()["total"] == 1
    assert client.get(B, headers=h, params={"region": "SOUT"}).json()["total"] == 2
    assert client.get(B, headers=h, params={"region": world["north"].id}).json()["total"] == 1
    assert client.get(B, headers=h, params={"age_days": 1}).json()["total"] == 0
    page = client.get(B, headers=h, params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert {"id", "rule_code", "state", "reason", "institution_name", "age_days",
            "lock_version", "record_count"} <= set(page["items"][0])
    assert client.get(B, headers=h, params={"state": "bogus"}).status_code == 422


def test_age_filter_counts_days_on_the_demo_clock(client, login, db, scene):
    h = login("admin@demo.test")
    for f in db.scalars(select(ValidationFlag)):
        f.created_at = clock.now() - timedelta(days=10)
    db.commit()
    assert client.get(B, headers=h, params={"age_days": 7}).json()["total"] == 3
    assert client.get(B, headers=h, params={"age_days": 11}).json()["total"] == 0


# ---- detail ------------------------------------------------------------------------------------

def test_detail_has_evidence_records_rule_snapshot_events_and_is_audited(
        client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R02")
    d = client.get(f"{B}/{f.id}", headers=login("officer.south@demo.test")).json()
    assert d["rule_code"] == "R02" and d["evidence"]["digits_found"] == 11
    assert d["rule_version"]["version_no"] == 1 and d["rule_version"]["params"]["digits"] == 12
    assert d["records"][0]["apaar_id"] == "99990000002" and d["records"][0]["row_number"] == 2
    assert d["events"][0]["to_state"] == "raised"
    assert "FLAG.VIEWED" in audit_actions(db)


def test_detail_outside_scope_refused_and_audited(client, login, db, world, scene):
    f = flag(db, world["northfield"], "R03")
    for who in ("officer.south@demo.test", "kaveri.admin@demo.test"):
        assert client.get(f"{B}/{f.id}", headers=login(who)).status_code == 403
    assert audit_actions(db).count("ACCESS.REFUSED") == 2
    assert client.get(f"{B}/nope", headers=login("admin@demo.test")).status_code == 404


# ---- actions -----------------------------------------------------------------------------------

def test_review_assigns_actor_and_records_event_audit_and_notifies(
        client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R02")
    r = act(client, login("officer.south@demo.test"), f.id, "review", note="taking this")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["state"] == "under_review" and out["lock_version"] == 2
    assert out["assignee_id"] == world["users"]["officer_south"].id
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == f.id)
                    .order_by(FlagEvent.at)).all()[-1]
    assert (ev.from_state, ev.to_state, ev.note) == ("open", "under_review", "taking this")
    assert ev.actor_id == world["users"]["officer_south"].id
    assert "FLAG.REVIEWED" in audit_actions(db)
    n = db.scalars(select(Notification).where(
        Notification.related_id == f.id, Notification.channel == "IN_APP")).all()
    assert {x.user_id for x in n} == {world["users"]["inst_admin"].id,
                                      world["users"]["inst_staff"].id}


@pytest.mark.parametrize("action,state", [("resolve", "resolved"), ("dismiss", "dismissed"),
                                          ("ask", "ask_institution")])
def test_actions_from_open(client, login, db, world, scene, action, state):
    f = flag(db, world["kaveri"], "R01")
    r = act(client, login("admin@demo.test"), f.id, action)
    assert r.status_code == 200 and r.json()["state"] == state


@pytest.mark.parametrize("action", ["review", "resolve", "dismiss", "ask", "link", "reply"])
def test_note_is_required(client, login, db, world, scene, action):
    f = flag(db, world["kaveri"], "R01")
    h = login("kaveri.admin@demo.test" if action == "reply" else "admin@demo.test")
    assert act(client, h, f.id, action, note=None).status_code == 422
    assert act(client, h, f.id, action, note="   ").status_code == 422
    assert db.get(ValidationFlag, f.id).state == "open"


def test_terminal_flag_cannot_move_and_bad_transition_is_409(client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R01")
    h = login("admin@demo.test")
    assert act(client, h, f.id, "dismiss").status_code == 200
    for a in ("review", "resolve", "ask"):
        assert act(client, h, f.id, a).status_code == 409
    g = flag(db, world["kaveri"], "R02")
    act(client, h, g.id, "review")
    assert act(client, h, g.id, "review").status_code == 409  # already under review


def test_stale_lock_version_is_409_and_current_one_wins(client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R01")
    h = login("admin@demo.test")
    assert act(client, h, f.id, "review", lock_version=1).status_code == 200
    r = act(client, h, f.id, "resolve", lock_version=1)
    assert r.status_code == 409 and db.get(ValidationFlag, f.id).state == "under_review"
    assert act(client, h, f.id, "resolve", lock_version=2).status_code == 200


def test_officer_outside_region_refused_and_audited(client, login, db, world, scene):
    f = flag(db, world["northfield"], "R03")
    r = act(client, login("officer.south@demo.test"), f.id, "resolve")
    assert r.status_code == 403
    assert db.get(ValidationFlag, f.id).state == "open"
    refusal = db.scalars(select(AuditLog).where(AuditLog.action == "ACCESS.REFUSED")).all()
    assert refusal and refusal[-1].entity_id == f.id


@pytest.mark.parametrize("action", ["review", "resolve", "dismiss", "ask", "link"])
def test_institution_roles_cannot_act(client, login, db, world, scene, action):
    f = flag(db, world["kaveri"], "R01")
    assert act(client, login("kaveri.admin@demo.test"), f.id, action).status_code == 403
    assert db.get(ValidationFlag, f.id).state == "open"


def test_ask_then_reply_returns_to_under_review_and_tells_officers(
        client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R01")
    r = act(client, login("officer.south@demo.test"), f.id, "ask", note="please explain")
    assert r.json()["state"] == "ask_institution"
    # a reply is only for the institution that owns the flag
    assert act(client, login("malabar.admin@demo.test"), f.id, "reply").status_code == 403
    r = act(client, login("kaveri.staff@demo.test"), f.id, "reply", note="ID not issued yet")
    assert r.status_code == 200 and r.json()["state"] == "under_review"
    assert "FLAG.REPLIED" in audit_actions(db)
    got = db.scalars(select(Notification).where(
        Notification.related_id == f.id, Notification.channel == "IN_APP",
        Notification.user_id == world["users"]["officer_south"].id)).all()
    assert any("ID not issued yet" in n.body for n in got)
    assert act(client, login("kaveri.staff@demo.test"), f.id, "reply").status_code == 409


def test_reply_to_a_flag_nobody_asked_about_is_409(client, login, db, world, scene):
    f = flag(db, world["kaveri"], "R01")
    assert act(client, login("kaveri.staff@demo.test"), f.id, "reply").status_code == 409


# ---- R08 hook ----------------------------------------------------------------------------------

def _r08(db, world, rec_ids):
    from app.models.rules import RuleVersion
    from app.models.student import FlagRecord
    v = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == "R08")).one()
    f = ValidationFlag(rule_code="R08", rule_version_id=v.id, institution_id=world["kaveri"].id,
                       reason_key="near_duplicate", reason="Names are alike.",
                       evidence={"similarity": 0.93}, state="open")
    db.add(f)
    db.flush()
    for r in rec_ids:
        db.add(FlagRecord(flag_id=f.id, record_id=r))
    db.commit()
    return f


def test_link_resolves_an_r08_flag_and_keeps_the_note(client, login, db, world, scene):
    from app.models.student import StudentRecord
    ids = db.scalars(select(StudentRecord.id).where(StudentRecord.row_number.in_([1, 2]),
                                                    StudentRecord.is_current)).all()
    f = _r08(db, world, ids)
    r = act(client, login("officer.south@demo.test"), f.id, "link",
            note="same student, rows 1 and 2")
    assert r.status_code == 200 and r.json()["state"] == "resolved"
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == f.id)).all()[-1]
    assert ev.note.startswith("Linked as the same student") and "rows 1 and 2" in ev.note
    assert "FLAG.LINKED" in audit_actions(db)


def test_link_on_other_rules_is_409_and_r08_can_be_dismissed(client, login, db, world, scene):
    h = login("admin@demo.test")
    assert act(client, h, flag(db, world["kaveri"], "R01").id, "link").status_code == 409
    f = _r08(db, world, [])
    assert act(client, h, f.id, "dismiss", note="twins").json()["state"] == "dismissed"


# ---- notifications -----------------------------------------------------------------------------

def test_unread_count(client, login, db, world, scene):
    h = login("kaveri.admin@demo.test")
    n = client.get("/api/v1/notifications/unread-count", headers=h).json()["count"]
    assert n == len(client.get("/api/v1/notifications", headers=h, params={"unread": True}).json())
    assert n >= 1
    first = client.get("/api/v1/notifications", headers=h).json()[0]["id"]
    client.post(f"/api/v1/notifications/{first}/read", headers=h)
    assert client.get("/api/v1/notifications/unread-count", headers=h).json()["count"] == n - 1
