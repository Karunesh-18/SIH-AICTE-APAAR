"""Role x endpoint matrix. Every non-public route must appear here, or the meta-test fails."""
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
}
BODIES = {
    ("PATCH", "/api/v1/auth/me"): {"language": "en"},
    ("POST", "/api/v1/admin/clock"): {"reset": True},
    ("PUT", "/api/v1/admin/rules/R02"): {"enabled": True, "note": "matrix"},
    ("POST", "/api/v1/admin/rules/R02/revert"): {"to_version": 1, "note": "matrix"},
    ("POST", "/api/v1/institutions/{kaveri}/students"): {"cycle_year": 2026, "students": []},
    ("POST", "/api/v1/institutions/{northfield}/students"): {"cycle_year": 2026, "students": []},
    ("POST", "/api/v1/institutions/{kaveri}/api-keys"): {"name": "matrix"},
}
QUERY = {("GET", "/api/v1/admin/rules/R02/diff"): {"from": 1, "to": 1}}


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
    from app.models.student import StudentRecord
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
    path = tpl.format(kaveri=world["kaveri"].id, northfield=world["northfield"].id,
                      notification=_admin_notification(db, world), upload=up, record=record,
                      key=key)
    headers = {} if role == "anon" else login(EMAIL[role])
    kw = {}
    if (method, tpl) == ("POST", "/api/v1/uploads"):
        kw = {"data": {"cycle_year": "2026", "institution_id": world["kaveri"].id},
              "files": {"file": ("a.csv", csv_bytes([row(2)]), "text/csv")}}
    else:
        kw = {"json": BODIES.get((method, tpl)), "params": QUERY.get((method, tpl))}
    r = client.request(method, path, headers=headers, **kw)
    assert r.status_code == expected, r.text


def test_every_route_is_in_the_matrix():
    seen = set()
    for route in create_app().routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/v1"):
            continue
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}:
            seen.add((method, path))
    # Normalise matrix templates ({kaveri} -> {institution_id})
    covered = {(m, t.replace("{kaveri}", "{institution_id}").replace(
        "{northfield}", "{institution_id}").replace(
        "{notification}", "{notification_id}").replace("{upload}", "{upload_id}").replace(
        "{record}", "{record_id}").replace("{key}", "{key_id}").replace(
        "/rules/R02", "/rules/{code}")) for (m, t) in MATRIX} | PUBLIC
    assert seen - covered == set(), f"routes missing from permission matrix: {seen - covered}"
