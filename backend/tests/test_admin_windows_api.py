"""Phase 5 admin endpoints: windows CRUD, run-cycle, anomaly run, regions, clock shape."""
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.windows import SubmissionWindow

A = "/api/v1/admin"
BODY = {"cycle_year": 2026, "institution_type": None, "opens_at": "2026-06-01T00:00:00Z",
        "closes_at": "2026-09-30T12:00:00Z",
        "ladder": [{"step": "T-7d", "offset_hours": -168, "audience": "institution"}]}


def test_windows_crud_is_admin_only_and_audited(client, login, db):
    h = login("admin@demo.test")
    r = client.post(f"{A}/windows", headers=h, json=BODY)
    assert r.status_code == 201, r.text
    wid = r.json()["id"]
    assert client.get(f"{A}/windows", headers=h).json()[0]["ladder"][0]["step"] == "T-7d"
    up = client.put(f"{A}/windows/{wid}", headers=h, json=BODY | {"cycle_year": 2027})
    assert up.status_code == 200 and up.json()["cycle_year"] == 2027
    assert client.put(f"{A}/windows/nope", headers=h, json=BODY).status_code == 404
    acts = [a.action for a in db.scalars(select(AuditLog))]
    assert "WINDOW.CREATED" in acts and "WINDOW.UPDATED" in acts
    assert client.get(f"{A}/windows", headers=login("officer.south@demo.test")).status_code == 403


def test_window_validation(client, login):
    h = login("admin@demo.test")
    bad = BODY | {"closes_at": "2026-05-01T00:00:00Z"}
    assert client.post(f"{A}/windows", headers=h, json=bad).status_code == 422
    dup = BODY | {"ladder": BODY["ladder"] * 2}
    assert client.post(f"{A}/windows", headers=h, json=dup).status_code == 422
    assert client.post(f"{A}/windows", headers=h, json=BODY | {"x": 1}).status_code == 422


def test_run_cycle_and_anomaly_endpoints(client, login, db, world, rules):
    h = login("admin@demo.test")
    client.post(f"{A}/windows", headers=h, json=BODY | {"closes_at": "2026-06-10T00:00:00Z"})
    r = client.post(f"{A}/windows/run-cycle", headers=h)
    assert r.status_code == 200 and {"sent", "skipped", "late", "flags"} <= set(r.json())
    r = client.post(f"{A}/anomaly/run", headers=h)
    assert r.status_code == 200 and "raised" in r.json()
    assert db.scalars(select(SubmissionWindow)).first()


def test_clock_response_has_now_and_offset(client, login):
    r = client.get(f"{A}/clock", headers=login("admin@demo.test")).json()
    assert "now" in r and "offset_days" in r


def test_regions(client, login, world):
    assert {r["code"] for r in client.get("/api/v1/regions", headers=login("admin@demo.test")).json()} \
        == {"SOUT", "NORT"}
    off = client.get("/api/v1/regions", headers=login("officer.south@demo.test")).json()
    assert [r["code"] for r in off] == ["SOUT"]
    assert client.get("/api/v1/regions", headers=login("verifier@demo.test")).status_code == 403
