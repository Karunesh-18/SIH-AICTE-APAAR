"""Role x endpoint matrix. Every non-public route must appear here, or the meta-test fails."""
import pytest

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
    ("GET", "/api/v1/admin/clock"): row(admin=200),
    ("POST", "/api/v1/admin/clock"): row(admin=200),
}
BODIES = {
    ("PATCH", "/api/v1/auth/me"): {"language": "en"},
    ("POST", "/api/v1/admin/clock"): {"reset": True},
}


def _cases():
    for (method, tpl), expected in MATRIX.items():
        for role in ROLES:
            yield pytest.param(method, tpl, role, expected[role], id=f"{role}-{method}-{tpl}")


@pytest.mark.parametrize("method,tpl,role,expected", list(_cases()))
def test_matrix(client, login, world, method, tpl, role, expected):
    path = tpl.format(kaveri=world["kaveri"].id, northfield=world["northfield"].id)
    headers = {} if role == "anon" else login(EMAIL[role])
    r = client.request(method, path, headers=headers, json=BODIES.get((method, tpl)))
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
        "{northfield}", "{institution_id}")) for (m, t) in MATRIX} | PUBLIC
    assert seen - covered == set(), f"routes missing from permission matrix: {seen - covered}"
