"""Phase 5: shared metrics, dashboards and the dashboard == report consistency check."""
import pytest

from app.models.student import StudentRecord, ValidationFlag
from tests.phase5_helpers import dash_scene

D = "/api/v1/dashboards"


@pytest.fixture
def scene(db, world, rules):
    dash_scene(db, world)


def table(body):
    return {r["name"]: r for r in body["institutions"]}


def test_aicte_dashboard_tiles_and_table(client, login, scene):
    body = client.get(f"{D}/aicte", headers=login("admin@demo.test")).json()
    t = body["tiles"]
    assert (t["institutions"], t["records"], t["excess"], t["alert"]) == (3, 8, 1, 1)
    assert t["open_flags"] >= 3 and t["pending_apaar_share"] == 12.5
    k = table(body)["Kaveri Valley College"]
    assert (k["state"], k["enrolled"], k["allowed"], k["approved_intake"]) == ("Excess", 5, 4, 4)
    assert k["flags"]["R06"] == 1 and k["last_upload"] is not None
    assert table(body)["Malabar Pharmacy College"]["state"] == "Alert"
    n = table(body)["Northfield Institute"]
    assert n["state"] == "Clear" and n["last_upload"] is None


def test_officer_sees_only_own_regions(client, login, scene):
    body = client.get(f"{D}/aicte", headers=login("officer.south@demo.test")).json()
    assert body["tiles"]["institutions"] == 2
    assert "Northfield Institute" not in table(body)


def test_filters(client, login, scene):
    h = login("admin@demo.test")
    assert list(table(client.get(f"{D}/aicte", headers=h, params={"state": "Alert"}).json())) == [
        "Malabar Pharmacy College"]
    r = client.get(f"{D}/aicte", headers=h, params={"region": "NORT"}).json()
    assert list(table(r)) == ["Northfield Institute"]
    r = client.get(f"{D}/aicte", headers=h, params={"type": "PHARMACY"}).json()
    assert list(table(r)) == ["Malabar Pharmacy College"]


def test_withdrawn_and_superseded_rows_do_not_count(client, login, db, scene):
    recs = db.query(StudentRecord).order_by(StudentRecord.row_number).all()
    kaveri = [r for r in recs if r.programme_id == recs[0].programme_id]
    kaveri[0].status = "withdrawn"
    kaveri[1].is_current = False  # superseded
    db.commit()
    body = client.get(f"{D}/aicte", headers=login("admin@demo.test")).json()
    assert body["tiles"]["records"] == 6
    assert table(body)["Kaveri Valley College"]["enrolled"] == 3


def test_over_cap_is_excess_even_if_the_flag_was_closed(client, login, db, scene):
    for f in db.query(ValidationFlag).filter_by(rule_code="R06"):
        f.state = "dismissed"
    db.commit()
    k = table(client.get(f"{D}/aicte", headers=login("admin@demo.test")).json())[
        "Kaveri Valley College"]
    assert k["state"] == "Excess"  # 5 enrolled against 4 allowed


def test_institution_dashboard(client, login, scene):
    body = client.get(f"{D}/institution", headers=login("kaveri.staff@demo.test")).json()
    assert body["institution"]["name"] == "Kaveri Valley College"
    assert body["window"] is None
    assert body["records"]["accepted"] == 5 and body["records"]["flagged"] >= 1
    assert any(f["rule"] == "R06" for f in body["todo"]["open_flags"])
    assert body["todo"]["asks"] == []


def test_institution_dashboard_scope(client, login, scene, world):
    h = login("kaveri.staff@demo.test")
    r = client.get(f"{D}/institution", headers=h, params={"institution_id": world["malabar"].id})
    assert r.status_code == 403
    assert client.get(f"{D}/institution", headers=login("admin@demo.test")).status_code == 422
    r = client.get(f"{D}/institution", headers=login("admin@demo.test"),
                   params={"institution_id": world["malabar"].id}).json()
    assert r["records"]["pending_apaar"] == 1 and len(r["todo"]["pending_apaar"]) == 1
    assert "name" not in r["todo"]["pending_apaar"][0]
    r = client.get(f"{D}/institution", headers=login("officer.south@demo.test"),
                   params={"institution_id": world["northfield"].id})
    assert r.status_code == 403


def test_intake_use_and_flags_trend(client, login, scene):
    h = login("admin@demo.test")
    rows = client.get(f"{D}/intake-use", headers=h).json()["rows"]
    k = next(r for r in rows if r["institution"] == "Kaveri Valley College")
    assert (k["enrolled"], k["approved_intake"], k["allowed"]) == (5, 4, 4)
    trend = client.get(f"{D}/flags-trend", headers=h).json()["rows"]
    assert all(set(r) == {"month", "rule", "count"} for r in trend)
    assert sum(r["count"] for r in trend) >= 3
    own = client.get(f"{D}/intake-use", headers=login("kaveri.admin@demo.test")).json()["rows"]
    assert {r["institution"] for r in own} == {"Kaveri Valley College"}


def test_dashboard_numbers_equal_report_numbers(client, login, scene):
    h = login("admin@demo.test")
    R = "/api/v1/reports"
    dash = client.get(f"{D}/aicte", headers=h).json()
    rep = client.get(f"{R}/enrolment_vs_intake", headers=h).json()
    assert sum(r["enrolled"] for r in rep["rows"]) == dash["tiles"]["records"]
    pend = client.get(f"{R}/pending_apaar_share", headers=h).json()
    assert pend["total"]["share_pct"] == dash["tiles"]["pending_apaar_share"]
    by_inst = {r["institution"]: r for r in client.get(
        f"{R}/enrolment_vs_intake", headers=h, params={"group_by": "institution"}).json()["rows"]}
    for r in dash["institutions"]:
        assert by_inst[r["name"]]["enrolled"] == r["enrolled"]
        assert by_inst[r["name"]]["allowed"] == r["allowed"]
    flags = client.get(f"{R}/flags_by_rule_month", headers=h).json()["rows"]
    trend = client.get(f"{D}/flags-trend", headers=h).json()["rows"]
    key = lambda r: (r["month"], r["rule"])
    assert sorted(flags, key=key) == sorted(trend, key=key)
