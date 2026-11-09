"""HTTP surface of Phase 3: uploads, templates, records, JSON push, API keys, rule admin."""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.student import StudentRecord
from tests.ingest_helpers import csv_bytes, programme, register, row

BASE = "/api/v1"


@pytest.fixture
def setup(db, world, rules):
    programme(db, world["kaveri"], intake=10)
    programme(db, world["northfield"], name="B.Tech", intake=10)
    programme(db, world["malabar"], name="B.Pharm", intake=10)
    return world


def upload(client, headers, rows, cycle=2026, institution_id=None, name="s.csv", data=None):
    form = {"cycle_year": str(cycle)}
    if institution_id:
        form["institution_id"] = institution_id
    return client.post(f"{BASE}/uploads", headers=headers, data=form,
                       files={"file": (name, csv_bytes(rows) if data is None else data, "text/csv")})


def test_upload_returns_202_receipt_then_poll_shows_done(client, login, db, setup):
    rows = [row(n) for n in range(1, 4)]
    register(db, rows)
    h = login("kaveri.staff@demo.test")
    r = upload(client, h, rows)
    assert r.status_code == 202 and set(r.json()) >= {"id", "status"}
    got = client.get(f"{BASE}/uploads/{r.json()['id']}", headers=h).json()
    assert got["status"] == "DONE" and got["row_count"] == 3 and got["flagged_count"] == 0
    assert got["flags"] == {"total": 0, "by_rule": {}}


def test_poll_shows_flag_summary_and_rejection_message(client, login, db, setup):
    h = login("kaveri.staff@demo.test")
    good = upload(client, h, [row(1, apaar_id="12")]).json()["id"]
    flags = client.get(f"{BASE}/uploads/{good}", headers=h).json()["flags"]
    assert flags == {"total": 1, "by_rule": {"R02": 1}}
    bad = upload(client, h, [], data=b"").json()["id"]
    got = client.get(f"{BASE}/uploads/{bad}", headers=h).json()
    assert got["status"] == "REJECTED" and "empty" in got["error"].lower()


def test_institution_user_cannot_upload_for_another_institution(client, login, setup, world):
    h = login("kaveri.staff@demo.test")
    r = upload(client, h, [row(1)], institution_id=world["northfield"].id)
    assert r.status_code == 403


def test_aicte_admin_needs_an_institution_id(client, login, setup, world):
    h = login("admin@demo.test")
    assert upload(client, h, [row(1)]).status_code == 422
    assert upload(client, h, [row(1)], institution_id=world["northfield"].id).status_code == 202


def test_officer_is_scoped_to_their_region(client, login, setup, world):
    h = login("officer.south@demo.test")
    assert upload(client, h, [row(1)], institution_id=world["northfield"].id).status_code == 403
    assert upload(client, h, [row(1)], institution_id=world["kaveri"].id).status_code == 202


def test_list_and_get_uploads_are_scoped(client, login, setup, world):
    k, n = login("kaveri.staff@demo.test"), login("admin@demo.test")
    mine = upload(client, k, [row(1)]).json()["id"]
    other = upload(client, n, [row(2)], institution_id=world["northfield"].id).json()["id"]
    ids = [u["id"] for u in client.get(f"{BASE}/uploads", headers=k).json()["items"]]
    assert ids == [mine]
    assert client.get(f"{BASE}/uploads/{other}", headers=k).status_code == 403
    assert client.get(f"{BASE}/uploads/nope", headers=k).status_code == 404
    assert len(client.get(f"{BASE}/uploads", headers=n).json()["items"]) == 2


@pytest.mark.parametrize("fmt,ctype", [("csv", "text/csv"), ("xlsx", "spreadsheetml")])
def test_templates_download(client, login, fmt, ctype):
    r = client.get(f"{BASE}/templates/{fmt}", headers=login("kaveri.staff@demo.test"))
    assert r.status_code == 200 and ctype in r.headers["content-type"] and r.content
    assert client.get(f"{BASE}/templates/pdf", headers=login("admin@demo.test")).status_code == 404


def test_records_list_paginated_and_filtered_by_status(client, login, db, setup, world):
    rows = [row(n) for n in range(1, 6)] + [row(6, apaar_id="")]
    register(db, rows)
    h = login("kaveri.staff@demo.test")
    upload(client, h, rows)
    url = f"{BASE}/institutions/{world['kaveri'].id}/records"
    page = client.get(url, headers=h, params={"limit": 4}).json()
    assert page["total"] == 6 and len(page["items"]) == 4
    pend = client.get(url, headers=h, params={"status": "pending_apaar"}).json()
    assert pend["total"] == 1 and pend["items"][0]["apaar_id"] is None
    assert client.get(url, headers=h, params={"status": "bogus"}).status_code == 422
    other = f"{BASE}/institutions/{world['northfield'].id}/records"
    assert client.get(other, headers=h).status_code == 403


def test_single_record_view_is_audited_with_version_history(client, login, db, setup):
    h = login("kaveri.staff@demo.test")
    rows = [row(1)]
    register(db, rows)
    upload(client, h, rows)
    upload(client, h, rows)
    cur = db.scalars(select(StudentRecord).where(StudentRecord.is_current)).one()
    r = client.get(f"{BASE}/records/{cur.id}", headers=h)
    body = r.json()
    assert r.status_code == 200 and body["version"] == 2
    assert [v["version"] for v in body["versions"]] == [1, 2]
    assert db.scalars(select(AuditLog).where(AuditLog.action == "RECORD.VIEWED",
                                             AuditLog.entity_id == cur.id)).first()


def test_record_of_another_institution_is_refused_and_audited(client, login, db, setup, world):
    rows = [row(1)]
    register(db, rows)
    upload(client, login("admin@demo.test"), rows, institution_id=world["northfield"].id)
    rec = db.scalars(select(StudentRecord)).one()
    assert client.get(f"{BASE}/records/{rec.id}", headers=login("kaveri.staff@demo.test")
                      ).status_code == 403
    assert db.scalars(select(AuditLog).where(AuditLog.action == "ACCESS.REFUSED")).first()


def test_serializer_masks_for_outside_viewers():
    from types import SimpleNamespace as NS

    from app.api.records import mask_record

    rec = {"apaar_id": "999900000001", "name": "Asha Rao", "dob": "2001-03-04"}
    own = mask_record(rec, NS(role="INSTITUTION_STAFF", institution_id="i1"), "i1")
    assert own == rec
    officer = mask_record(rec, NS(role="AICTE_OFFICER", institution_id=None), "i1")
    assert officer == rec
    outside = mask_record(rec, NS(role="VERIFIER", institution_id=None), "i1")
    assert outside["apaar_id"] == "XXXX XXXX 0001"
    assert outside["name"] != "Asha Rao" and outside["dob"] != "2001-03-04"


# ---- JSON push and API keys -------------------------------------------------------------------

def make_key(client, headers, inst_id):
    r = client.post(f"{BASE}/institutions/{inst_id}/api-keys", headers=headers,
                    json={"name": "ERP sync"})
    assert r.status_code == 201, r.text
    return r.json()


def test_api_key_shown_once_stored_hashed_and_listed_by_prefix(client, login, db, setup, world):
    h = login("kaveri.admin@demo.test")
    made = make_key(client, h, world["kaveri"].id)
    assert made["key"].startswith("wmk_") and made["prefix"] == made["key"][:8]
    listed = client.get(f"{BASE}/institutions/{world['kaveri'].id}/api-keys", headers=h).json()
    assert [k["prefix"] for k in listed] == [made["prefix"]]
    assert "key" not in listed[0] and "key_hash" not in listed[0]
    from app.models.system import ApiKey

    stored = db.scalars(select(ApiKey)).one()
    assert made["key"] not in (stored.key_hash, stored.prefix) and len(stored.key_hash) == 64


def test_only_institution_admin_of_that_institution_or_admin_manage_keys(client, login, setup,
                                                                          world):
    url = f"{BASE}/institutions/{world['kaveri'].id}/api-keys"
    assert client.post(url, headers=login("kaveri.staff@demo.test"), json={"name": "x"}
                       ).status_code == 403
    assert client.post(url, headers=login("officer.south@demo.test"), json={"name": "x"}
                       ).status_code == 403
    other = f"{BASE}/institutions/{world['northfield'].id}/api-keys"
    assert client.post(other, headers=login("kaveri.admin@demo.test"), json={"name": "x"}
                       ).status_code == 403
    assert client.post(other, headers=login("admin@demo.test"), json={"name": "x"}
                       ).status_code == 201


def push(client, key, inst_id, rows, cycle=2026):
    return client.post(f"{BASE}/institutions/{inst_id}/students", headers={"X-API-Key": key},
                       json={"cycle_year": cycle, "students": rows})


def test_json_batch_with_api_key_and_every_use_is_audited(client, login, db, setup, world):
    rows = [row(1), row(2, apaar_id="12")]
    register(db, rows)
    made = make_key(client, login("kaveri.admin@demo.test"), world["kaveri"].id)
    r = push(client, made["key"], world["kaveri"].id, rows)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "DONE" and body["row_count"] == 2 and body["flagged_count"] == 1
    uses = db.scalars(select(AuditLog).where(AuditLog.action == "APIKEY.USED")).all()
    assert len(uses) == 1 and uses[0].entity_id == made["id"]
    push(client, made["key"], world["kaveri"].id, rows)
    assert len(db.scalars(select(AuditLog).where(AuditLog.action == "APIKEY.USED")).all()) == 2


def test_api_key_is_bound_to_its_institution_and_revocable(client, login, db, setup, world):
    made = make_key(client, login("kaveri.admin@demo.test"), world["kaveri"].id)
    assert push(client, made["key"], world["northfield"].id, [row(1)]).status_code == 403
    assert push(client, "wmk_garbage", world["kaveri"].id, [row(1)]).status_code == 401
    d = client.delete(f"{BASE}/institutions/{world['kaveri'].id}/api-keys/{made['id']}",
                      headers=login("kaveri.admin@demo.test"))
    assert d.status_code == 200
    assert push(client, made["key"], world["kaveri"].id, [row(1)]).status_code == 401
    assert db.scalars(select(AuditLog).where(AuditLog.action == "APIKEY.REVOKED")).first()


def test_json_batch_with_jwt(client, login, db, setup, world):
    rows = [row(1)]
    register(db, rows)
    r = client.post(f"{BASE}/institutions/{world['kaveri'].id}/students",
                    headers=login("kaveri.staff@demo.test"),
                    json={"cycle_year": 2026, "students": rows})
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    no_auth = client.post(f"{BASE}/institutions/{world['kaveri'].id}/students",
                          json={"cycle_year": 2026, "students": rows})
    assert no_auth.status_code == 401
    bad = client.post(f"{BASE}/institutions/{world['kaveri'].id}/students",
                      headers=login("kaveri.staff@demo.test"), json={"cycle_year": 2026})
    assert bad.status_code == 422


# ---- rule versions ----------------------------------------------------------------------------

def test_rules_list_shows_active_version_and_params(client, login, rules):
    r = client.get(f"{BASE}/admin/rules", headers=login("admin@demo.test")).json()
    r02 = next(x for x in r if x["code"] == "R02")
    assert r02["active"]["version_no"] == 1 and r02["active"]["params"]["digits"] == 12
    assert len(r) == 12


def test_put_creates_new_version_and_old_flags_keep_theirs(client, login, db, setup):
    k = login("kaveri.staff@demo.test")
    upload(client, k, [row(1, apaar_id="12")])
    a = login("admin@demo.test")
    r = client.put(f"{BASE}/admin/rules/R02", headers=a,
                   json={"params": {"digits": 12, "checksum": "verhoeff"}, "note": "Turn on check"})
    assert r.status_code == 200 and r.json()["version_no"] == 2
    vs = client.get(f"{BASE}/admin/rules/R02/versions", headers=a).json()
    assert [(v["version_no"], v["is_active"]) for v in vs] == [(2, True), (1, False)]
    from app.models.student import ValidationFlag

    old = db.scalars(select(ValidationFlag).where(ValidationFlag.rule_code == "R02")).one()
    from app.models.rules import RuleVersion

    assert db.get(RuleVersion, old.rule_version_id).version_no == 1
    diff = client.get(f"{BASE}/admin/rules/R02/diff", headers=a, params={"from": 1, "to": 2}).json()
    assert diff["changes"]["params"] == {"from": {"digits": 12, "checksum": "none"},
                                         "to": {"digits": 12, "checksum": "verhoeff"}}
    assert "message_en" not in diff["changes"]


def test_put_and_revert_need_a_note(client, login, rules):
    a = login("admin@demo.test")
    assert client.put(f"{BASE}/admin/rules/R02", headers=a, json={"enabled": False}
                      ).status_code == 422
    assert client.put(f"{BASE}/admin/rules/R02", headers=a, json={"enabled": False, "note": " "}
                      ).status_code == 422
    assert client.post(f"{BASE}/admin/rules/R02/revert", headers=a, json={"to_version": 1}
                       ).status_code == 422
    assert client.put(f"{BASE}/admin/rules/R99", headers=a, json={"enabled": False, "note": "x"}
                      ).status_code == 404


def test_revert_copies_old_version_into_a_new_one(client, login, rules):
    a = login("admin@demo.test")
    client.put(f"{BASE}/admin/rules/R02", headers=a,
               json={"params": {"digits": 10, "checksum": "none"}, "note": "try ten"})
    r = client.post(f"{BASE}/admin/rules/R02/revert", headers=a,
                    json={"to_version": 1, "note": "back to twelve"})
    assert r.status_code == 200 and r.json()["version_no"] == 3
    assert r.json()["params"] == {"digits": 12, "checksum": "none"} and r.json()["is_active"]
    assert client.post(f"{BASE}/admin/rules/R02/revert", headers=a,
                       json={"to_version": 9, "note": "x"}).status_code == 404


def test_rule_changes_are_audited(client, login, db, rules):
    a = login("admin@demo.test")
    client.put(f"{BASE}/admin/rules/R06", headers=a, json={"enabled": False, "note": "pause"})
    assert db.scalars(select(AuditLog).where(AuditLog.action == "RULE.UPDATED")).first()
