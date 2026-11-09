"""Phase 5 reports: catalogue, filters, CSV, saved definitions, audit, identity fields, scope."""
import csv
import io

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.ingest_helpers import programme, row
from tests.phase5_helpers import dash_scene, upload

R = "/api/v1/reports"
KEYS = {"enrolment_vs_intake", "flags_by_rule_month", "late_submitters", "pending_apaar_share",
        "duplicate_cases", "category_counts"}


@pytest.fixture
def scene(db, world, rules):
    dash_scene(db, world)


def test_catalogue(client, login, scene):
    r = client.get(R, headers=login("admin@demo.test")).json()
    assert {c["key"] for c in r} == KEYS and all(c["title"] and c["filters"] for c in r)


@pytest.mark.parametrize("key", sorted(KEYS))
def test_every_report_runs_as_json_and_csv(client, login, scene, key):
    h = login("admin@demo.test")
    j = client.get(f"{R}/{key}", headers=h).json()
    assert j["key"] == key and "columns" in j and isinstance(j["rows"], list)
    c = client.get(f"{R}/{key}", headers=h, params={"format": "csv"})
    assert c.status_code == 200 and c.headers["content-type"].startswith("text/csv")
    parsed = list(csv.reader(io.StringIO(c.text)))
    assert parsed[0] == j["columns"] and len(parsed) == len(j["rows"]) + 1


def test_unknown_report_and_format(client, login, scene):
    h = login("admin@demo.test")
    assert client.get(f"{R}/nope", headers=h).status_code == 404
    assert client.get(f"{R}/category_counts", headers=h, params={"format": "pdf"}).status_code == 422


def test_export_is_audited_with_filters_and_row_count(client, login, db, scene):
    h = login("admin@demo.test")
    r = client.get(f"{R}/enrolment_vs_intake", headers=h,
                   params={"format": "csv", "region": "SOUT", "group_by": "institution"})
    e = db.scalars(select(AuditLog).where(AuditLog.action == "REPORT.EXPORTED")).one()
    assert e.after["filters"]["region"] == "SOUT" and e.after["format"] == "csv"
    assert e.after["rows"] == len(list(csv.reader(io.StringIO(r.text)))) - 1
    assert e.entity_id == "enrolment_vs_intake"


def test_no_identity_fields_in_any_report(client, login, scene):
    text = "".join(client.get(f"{R}/{key}", headers=login("admin@demo.test")).text for key in KEYS)
    for banned in ("Student ", "2001-03-04", "dob", "9999000001", "999900000010"):
        assert banned not in text
    assert '"name"' not in text


def test_duplicate_cases_mask_ids(client, login, db, world, rules):
    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    upload(db, world["kaveri"], [row(1)])
    upload(db, world["northfield"], [row(1)])
    rows = client.get(f"{R}/duplicate_cases", headers=login("admin@demo.test")).json()["rows"]
    assert rows and all(r["rule"] in ("R05", "R08") for r in rows)
    assert "999900000001" not in str(rows) and "XXXX XXXX 0001" in str(rows)


def test_institution_scope(client, login, scene, world):
    h = login("kaveri.admin@demo.test")
    rows = client.get(f"{R}/enrolment_vs_intake", headers=h,
                      params={"group_by": "institution"}).json()["rows"]
    assert {r["institution"] for r in rows} == {"Kaveri Valley College"}
    r = client.get(f"{R}/enrolment_vs_intake", headers=h,
                   params={"institution_id": world["malabar"].id})
    assert r.status_code == 403
    own = client.get(f"{R}/enrolment_vs_intake", headers=h,
                     params={"institution_id": world["kaveri"].id})
    assert own.status_code == 200


def test_officer_scoped_to_regions(client, login, scene):
    rows = client.get(f"{R}/enrolment_vs_intake", headers=login("officer.south@demo.test"),
                      params={"group_by": "institution"}).json()["rows"]
    assert "Northfield Institute" not in {r["institution"] for r in rows}


def test_verifier_gets_nothing(client, login, scene):
    h = login("verifier@demo.test")
    assert client.get(R, headers=h).status_code == 403
    assert client.get(f"{R}/category_counts", headers=h).status_code == 403


def test_group_by_options(client, login, scene):
    h = login("admin@demo.test")
    for g in ("institution", "programme_type", "region"):
        rows = client.get(f"{R}/enrolment_vs_intake", headers=h,
                          params={"group_by": g}).json()["rows"]
        assert sum(r["enrolled"] for r in rows) == 8
    assert client.get(f"{R}/enrolment_vs_intake", headers=h,
                      params={"group_by": "x"}).status_code == 422


def test_saved_reports_per_user(client, login, db, scene):
    admin, staff = login("admin@demo.test"), login("kaveri.staff@demo.test")
    body = {"name": "South each cycle", "report_key": "enrolment_vs_intake",
            "filters": {"region": "SOUT"}}
    r = client.post(R, headers=admin, json=body)
    assert r.status_code == 201 and r.json()["id"]
    assert [s["name"] for s in client.get(f"{R}/saved", headers=admin).json()] == ["South each cycle"]
    assert client.get(f"{R}/saved", headers=staff).json() == []
    assert client.post(R, headers=admin, json=body | {"report_key": "nope"}).status_code == 422
    assert client.post(R, headers=admin, json=body | {"extra": 1}).status_code == 422
    assert db.scalars(select(AuditLog).where(AuditLog.action == "REPORT.SAVED")).one()
