"""Role x endpoint matrix. Every non-public route must appear here, or the meta-test fails."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.main import create_app

ROLES = ["admin", "officer_south", "inst_admin", "inst_staff", "verifier", "anon"]
EMAIL = {
    "admin": "admin@demo.test",
    "officer_south": "officer.south@demo.test",
    "inst_admin": "kaveri.admin@demo.test",
    "inst_staff": "kaveri.staff@demo.test",
    "verifier": "verifier@demo.test",
}
PUBLIC = {("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/refresh")}


def row(**expected):
    base = dict.fromkeys(ROLES, 403) | {"anon": 401}
    return base | expected


ALL_OK = {r: 200 for r in ROLES if r != "anon"}

# (method, route template) -> expected status per role
MATRIX = {
    ("GET", "/api/v1/auth/me"): row(**ALL_OK),
    ("PATCH", "/api/v1/auth/me"): row(**ALL_OK),
    ("GET", "/api/v1/institutions"): row(admin=200, officer_south=200, inst_admin=200,
                                         inst_staff=200),
    ("GET", "/api/v1/institutions/{kaveri}"): row(admin=200, officer_south=200,
                                                  inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/institutions/{northfield}"): row(admin=200),
    ("GET", "/api/v1/admin/audit"): row(admin=200),
    ("POST", "/api/v1/admin/audit/verify"): row(admin=200),
    ("POST", "/api/v1/admin/dev/tamper-audit"): row(admin=200),
    ("GET", "/api/v1/notifications"): row(**ALL_OK),
    ("GET", "/api/v1/notifications/unread-count"): row(**ALL_OK),
    # notification belongs to admin; everyone else gets 404, never someone else's data
    ("POST", "/api/v1/notifications/{notification}/read"): row(
        admin=200, officer_south=404, inst_admin=404, inst_staff=404, verifier=404),
    ("GET", "/api/v1/admin/clock"): row(admin=200),
    ("POST", "/api/v1/admin/clock"): row(admin=200),
    ("POST", "/api/v1/uploads"): row(admin=202, officer_south=202, inst_admin=202, inst_staff=202),
    ("GET", "/api/v1/uploads"): row(admin=200, officer_south=200, inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/uploads/{upload}"): row(admin=200, officer_south=200, inst_admin=200,
                                             inst_staff=200),
    ("GET", "/api/v1/templates/csv"): row(admin=200, officer_south=200, inst_admin=200,
                                          inst_staff=200),
    ("GET", "/api/v1/templates/xlsx"): row(admin=200, officer_south=200, inst_admin=200,
                                           inst_staff=200),
    ("GET", "/api/v1/institutions/{kaveri}/records"): row(admin=200, officer_south=200,
                                                          inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/institutions/{northfield}/records"): row(admin=200),
    ("GET", "/api/v1/records/{record}"): row(admin=200, officer_south=200, inst_admin=200,
                                             inst_staff=200),
    ("POST", "/api/v1/institutions/{kaveri}/students"): row(
        admin=200, officer_south=200, inst_admin=200, inst_staff=200),
    ("POST", "/api/v1/institutions/{northfield}/students"): row(admin=200),
    ("GET", "/api/v1/institutions/{kaveri}/api-keys"): row(admin=200, inst_admin=200),
    ("POST", "/api/v1/institutions/{kaveri}/api-keys"): row(admin=201, inst_admin=201),
    ("DELETE", "/api/v1/institutions/{kaveri}/api-keys/{key}"): row(admin=200, inst_admin=200),
    ("GET", "/api/v1/admin/rules"): row(admin=200),
    ("GET", "/api/v1/admin/rules/R02/versions"): row(admin=200),
    ("PUT", "/api/v1/admin/rules/R02"): row(admin=200),
    ("GET", "/api/v1/admin/rules/R02/diff"): row(admin=200),
    ("POST", "/api/v1/admin/rules/R02/revert"): row(admin=200),
    ("GET", "/api/v1/flags"): row(admin=200, officer_south=200, inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/flags/{flag}"): row(admin=200, officer_south=200, inst_admin=200,
                                         inst_staff=200),
    ("POST", "/api/v1/flags/{flag}/review"): row(admin=200, officer_south=200),
    ("POST", "/api/v1/flags/{flag}/resolve"): row(admin=200, officer_south=200),
    ("POST", "/api/v1/flags/{flag}/dismiss"): row(admin=200, officer_south=200),
    ("POST", "/api/v1/flags/{flag}/ask"): row(admin=200, officer_south=200),
    # the matrix flag is R03, not a near-duplicate: allowed roles get 409 from the rule check
    ("POST", "/api/v1/flags/{flag}/link"): row(admin=409, officer_south=409),
    # the test puts the flag in ask_institution first; only institution users may answer
    ("POST", "/api/v1/flags/{flag}/reply"): row(inst_admin=200, inst_staff=200),
    ("PATCH", "/api/v1/records/{record}"): row(admin=200, inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/regions"): row(admin=200, officer_south=200, inst_admin=200, inst_staff=200),
    ("GET", "/api/v1/dashboards/aicte"): row(admin=200, officer_south=200),
    ("GET", "/api/v1/dashboards/institution"): row(admin=200, officer_south=200, inst_admin=200,
                                                   inst_staff=200),
    ("GET", "/api/v1/dashboards/intake-use"): row(admin=200, officer_south=200, inst_admin=200,
                                                  inst_staff=200),
    ("GET", "/api/v1/dashboards/flags-trend"): row(admin=200, officer_south=200, inst_admin=200,
                                                   inst_staff=200),
    ("GET", "/api/v1/reports"): row(admin=200, officer_south=200, inst_admin=200, inst_staff=200),
    ("POST", "/api/v1/reports"): row(admin=201, officer_south=201, inst_admin=201, inst_staff=201),
    ("GET", "/api/v1/reports/saved"): row(admin=200, officer_south=200, inst_admin=200,
                                          inst_staff=200),
    ("GET", "/api/v1/reports/{report}"): row(admin=200, officer_south=200, inst_admin=200,
                                             inst_staff=200),
    ("GET", "/api/v1/admin/windows"): row(admin=200),
    ("POST", "/api/v1/admin/windows"): row(admin=201),
    ("PUT", "/api/v1/admin/windows/{window}"): row(admin=200),
    ("POST", "/api/v1/admin/windows/run-cycle"): row(admin=200),
    ("POST", "/api/v1/admin/anomaly/run"): row(admin=200),
    ("POST", "/api/v1/records/{record}/withdraw"): row(admin=200, inst_admin=200, inst_staff=200),
}
WINDOW = {"cycle_year": 2026, "opens_at": "2026-06-01T00:00:00Z",
          "closes_at": "2026-09-30T00:00:00Z",
          "ladder": [{"step": "T0", "offset_hours": 0, "audience": "institution"}]}
BODIES = {
    ("POST", "/api/v1/reports"): {"name": "m", "report_key": "category_counts", "filters": {}},
    ("POST", "/api/v1/admin/windows"): WINDOW,
    ("PUT", "/api/v1/admin/windows/{window}"): WINDOW,
    ("PATCH", "/api/v1/auth/me"): {"language": "en"},
    ("POST", "/api/v1/admin/clock"): {"reset": True},
    ("PUT", "/api/v1/admin/rules/R02"): {"enabled": True, "note": "matrix"},
    ("POST", "/api/v1/admin/rules/R02/revert"): {"to_version": 1, "note": "matrix"},
    ("POST", "/api/v1/institutions/{kaveri}/students"): {"cycle_year": 2026, "students": []},
    ("POST", "/api/v1/institutions/{northfield}/students"): {"cycle_year": 2026, "students": []},
    ("POST", "/api/v1/institutions/{kaveri}/api-keys"): {"name": "matrix"},
    ("PATCH", "/api/v1/records/{record}"): {"name": "Matrix Student"},
    ("POST", "/api/v1/records/{record}/withdraw"): {"reason": "matrix"},
    **{("POST", f"/api/v1/flags/{{flag}}/{a}"): {"note": "matrix"}
       for a in ("review", "resolve", "dismiss", "ask", "link", "reply")},
}
QUERY = {("GET", "/api/v1/admin/rules/R02/diff"): {"from": 1, "to": 1},
         ("GET", "/api/v1/dashboards/institution"): {"institution_id": "{kaveri}"}}


def _cases():
    for (method, tpl), expected in MATRIX.items():
        for role in ROLES:
            yield pytest.param(method, tpl, role, expected[role], id=f"{role}-{method}-{tpl}")


def _admin_notification(db, world):
    from sqlalchemy import select

    from app.db.session import uow
    from app.models.notify import Notification
    from app.services import notify

    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
    return db.scalars(select(Notification.id).where(
        Notification.channel == "IN_APP", Notification.user_id == world["users"]["admin"].id)).first()


@pytest.mark.parametrize("method,tpl,role,expected", list(_cases()))
def test_matrix(client, login, db, world, rules, method, tpl, role, expected):
    from app.models.student import StudentRecord, ValidationFlag
    from tests.ingest_helpers import csv_bytes, programme, row

    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    admin = login("admin@demo.test")
    up = client.post("/api/v1/uploads", headers=admin, data={
        "cycle_year": "2026", "institution_id": world["kaveri"].id},
        files={"file": ("a.csv", csv_bytes([row(1)]), "text/csv")}).json()["id"]
    key = client.post(f"/api/v1/institutions/{world['kaveri'].id}/api-keys", headers=admin,
                      json={"name": "m"}).json()["id"]
    record = db.scalars(select(StudentRecord.id)).first()
    flag = db.scalars(select(ValidationFlag)).first()  # R03: the row's ID is not in the registry
    if tpl.endswith("/reply"):
        flag.state = "ask_institution"
        db.commit()
    from app.models.windows import SubmissionWindow
    window = SubmissionWindow(cycle_year=2026, opens_at=datetime(2026, 6, 1, tzinfo=UTC),
                              closes_at=datetime(2026, 9, 30, tzinfo=UTC), ladder=[])
    db.add(window)
    db.commit()
    window_id = window.id
    path = tpl.format(flag=flag.id, kaveri=world["kaveri"].id, northfield=world["northfield"].id,
                      notification=_admin_notification(db, world), upload=up, record=record,
                      key=key, report="category_counts", window=window_id)
    headers = {} if role == "anon" else login(EMAIL[role])
    kw = {}
    if (method, tpl) == ("POST", "/api/v1/uploads"):
        kw = {"data": {"cycle_year": "2026", "institution_id": world["kaveri"].id},
              "files": {"file": ("a.csv", csv_bytes([row(2)]), "text/csv")}}
    else:
        params = {k: v.format(kaveri=world["kaveri"].id) if isinstance(v, str) else v
                  for k, v in (QUERY.get((method, tpl)) or {}).items()} or None
        kw = {"json": BODIES.get((method, tpl)), "params": params}
    r = client.request(method, path, headers=headers, **kw)
    assert r.status_code == expected, r.text


def test_every_route_is_in_the_matrix():
    seen = set()
    # openapi(): newer FastAPI wraps included routers, so app.routes no longer lists their paths
    for path, ops in create_app().openapi()["paths"].items():
        if path.startswith("/api/v1"):
            seen |= {(m.upper(), path) for m in ops}
    # Normalise matrix templates ({kaveri} -> {institution_id})
    covered = {(m, t.replace("{kaveri}", "{institution_id}").replace(
        "{northfield}", "{institution_id}").replace(
        "{notification}", "{notification_id}").replace("{upload}", "{upload_id}").replace(
        "{record}", "{record_id}").replace("{flag}", "{flag_id}").replace(
        "/templates/csv", "/templates/{fmt}").replace("/templates/xlsx", "/templates/{fmt}").replace("{key}", "{key_id}").replace("{report}", "{key}").replace("{window}", "{window_id}").replace(
        "/rules/R02", "/rules/{code}")) for (m, t) in MATRIX} | PUBLIC
    assert seen - covered == set(), f"routes missing from permission matrix: {seen - covered}"
