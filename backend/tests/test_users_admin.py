"""User and staff management: AICTE admin over all users, institution admin over own staff."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.user import User, UserRegion
from app.services import errors as E
from app.services import users as svc
from tests.conftest import PASSWORD

A = "/api/v1/admin/users"
GOOD = "Sturdy-pass-2026"


def actions(db):
    return [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]


def new_user(client, h, **kw):
    body = {"email": "new.officer@demo.test", "full_name": "New Officer", "role": "AICTE_OFFICER",
            "regions": ["SOUT"]} | kw
    return client.post(A, headers=h, json=body)


def sign_in(client, email, pw):
    return client.post("/api/v1/auth/login", json={"email": email, "password": pw}).status_code


# ---- AICTE admin -------------------------------------------------------------------------------

def test_list_users_has_no_secrets_and_filters(client, login, db, world):
    h = login("admin@demo.test")
    r = client.get(A, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5 and "password" not in r.text
    officer = next(u for u in body["items"] if u["role"] == "AICTE_OFFICER")
    assert officer["regions"] == ["SOUT"]
    only = client.get(A, headers=h, params={"role": "INSTITUTION_STAFF"}).json()
    assert [u["email"] for u in only["items"]] == ["kaveri.staff@demo.test"]


def test_create_officer_returns_a_temporary_password_once(client, login, db, world):
    h = login("admin@demo.test")
    r = new_user(client, h, email="New.Officer@Demo.test")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["user"]["email"] == "new.officer@demo.test" and out["user"]["regions"] == ["SOUT"]
    tmp = out["temporary_password"]
    assert len(tmp) >= 12
    assert sign_in(client, "new.officer@demo.test", tmp) == 200
    assert "temporary_password" not in client.get(A, headers=h).text
    rows = [a for a in db.scalars(select(AuditLog)) if a.action == "USER.CREATED"]
    assert len(rows) == 1 and tmp not in str(rows[0].after) and "hash" not in str(rows[0].after)


def test_create_with_chosen_password_echoes_nothing(client, login, db, world):
    r = new_user(client, login("admin@demo.test"), password=GOOD)
    assert r.status_code == 201 and "temporary_password" not in r.json()
    assert sign_in(client, "new.officer@demo.test", GOOD) == 200


@pytest.mark.parametrize("pw", ["short", "Demo@1234", "123456789"])
def test_weak_passwords_are_refused(client, login, db, world, pw):
    assert new_user(client, login("admin@demo.test"), password=pw).status_code == 422


def test_default_demo_password_refused_outside_demo_mode(client, login, db, world, monkeypatch):
    h = login("admin@demo.test")
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(svc, "DEMO_PASSWORDS", {GOOD})
    assert new_user(client, h, password=GOOD).status_code == 422
    monkeypatch.setattr(settings, "demo_mode", True)
    assert new_user(client, h, password=GOOD).status_code == 201


def test_email_must_be_unique_ignoring_case(client, login, db, world):
    assert new_user(client, login("admin@demo.test"), email="ADMIN@demo.test").status_code == 409


@pytest.mark.parametrize("kw", [
    {"role": "INSTITUTION_STAFF"},                                  # institution missing
    {"role": "AICTE_OFFICER", "institution_id": "x"},               # officers have no institution
    {"regions": ["NOPE"]},                                          # unknown region
    {"role": "VERIFIER"},                                           # verifiers self-register
    {"role": "SUPERUSER"},
    {"is_active": False},                                           # mass assignment
    {"password_hash": "x"},
    {"id": "abc"},
    {"email": "not-an-email"},
])
def test_bad_create_bodies(client, login, db, world, kw):
    assert new_user(client, login("admin@demo.test"), **kw).status_code == 422


def test_create_institution_staff_for_an_institution(client, login, db, world):
    r = new_user(client, login("admin@demo.test"), role="INSTITUTION_ADMIN", regions=[],
                 institution_id=world["malabar"].id)
    assert r.status_code == 201 and r.json()["user"]["institution_id"] == world["malabar"].id


def test_patch_changes_role_regions_and_active_flag(client, login, db, world):
    h = login("admin@demo.test")
    uid = world["users"]["officer_south"].id
    r = client.patch(f"{A}/{uid}", headers=h, json={"regions": ["SOUT", "NORT"]})
    assert r.status_code == 200 and sorted(r.json()["regions"]) == ["NORT", "SOUT"]
    assert client.patch(f"{A}/{uid}", headers=h, json={"is_active": False}).status_code == 200
    assert sign_in(client, "officer.south@demo.test", PASSWORD) == 401
    r = client.patch(f"{A}/{uid}", headers=h, json={"role": "INSTITUTION_STAFF",
                                                    "institution_id": world["malabar"].id,
                                                    "is_active": True})
    assert r.status_code == 200 and r.json()["role"] == "INSTITUTION_STAFF"
    assert r.json()["regions"] == []  # regions only belong to officers
    assert db.scalars(select(UserRegion).where(UserRegion.user_id == uid)).all() == []
    assert actions(db).count("USER.UPDATED") == 2
    assert actions(db).count("USER.DEACTIVATED") == 1


def test_patch_cannot_mass_assign(client, login, db, world):
    h = login("admin@demo.test")
    uid = world["users"]["inst_staff"].id
    for body in ({"password_hash": "x"}, {"email": "x@y.test"}, {"id": "1"}, {}):
        assert client.patch(f"{A}/{uid}", headers=h, json=body).status_code == 422


def test_admin_cannot_deactivate_or_demote_themselves(client, login, db, world):
    h = login("admin@demo.test")
    me = world["users"]["admin"].id
    assert client.patch(f"{A}/{me}", headers=h, json={"is_active": False}).status_code == 409
    assert client.patch(f"{A}/{me}", headers=h, json={"role": "AICTE_OFFICER",
                                                      "regions": ["SOUT"]}).status_code == 409


def test_the_last_active_admin_stays(db, world):
    other = User(email="b@demo.test", password_hash=hash_password(GOOD), full_name="b",
                 role="AICTE_ADMIN", is_active=False)
    db.add(other)
    db.commit()
    sole = world["users"]["admin"]
    with pytest.raises(E.Conflict):
        svc.update(db, other, sole.id, {"is_active": False})
    with pytest.raises(E.Conflict):
        svc.update(db, other, sole.id, {"role": "AICTE_OFFICER", "regions": ["SOUT"]})


def test_reset_password_sets_a_new_temporary_one(client, login, db, world):
    h = login("admin@demo.test")
    uid = world["users"]["inst_staff"].id
    r = client.post(f"{A}/{uid}/reset-password", headers=h)
    assert r.status_code == 200
    tmp = r.json()["temporary_password"]
    assert sign_in(client, "kaveri.staff@demo.test", PASSWORD) == 401
    assert sign_in(client, "kaveri.staff@demo.test", tmp) == 200
    entry = [a for a in db.scalars(select(AuditLog)) if a.action == "USER.PASSWORD_RESET"]
    assert len(entry) == 1 and tmp not in str(entry[0].after)
    assert client.post(f"{A}/nope/reset-password", headers=h).status_code == 404


def test_only_aicte_admin_manages_users(client, login, db, world):
    for who in ("officer.south@demo.test", "kaveri.admin@demo.test", "kaveri.staff@demo.test",
                "verifier@demo.test"):
        h = login(who)
        assert client.get(A, headers=h).status_code == 403
        assert new_user(client, h).status_code == 403
    assert client.get(A).status_code == 401


# ---- institution admin over own staff ----------------------------------------------------------

def S(inst):
    return f"/api/v1/institutions/{inst.id}/staff"


def mal_staff(db, world):
    other = User(email="mal.staff@demo.test", password_hash=hash_password(PASSWORD), full_name="m",
                 role="INSTITUTION_STAFF", institution_id=world["malabar"].id)
    db.add(other)
    db.commit()
    return other


def test_institution_admin_lists_only_own_staff(client, login, db, world):
    mal_staff(db, world)
    r = client.get(S(world["kaveri"]), headers=login("kaveri.admin@demo.test"))
    assert [u["email"] for u in r.json()["items"]] == ["kaveri.staff@demo.test"]


def test_institution_admin_creates_staff_with_a_forced_role_and_institution(
        client, login, db, world):
    h = login("kaveri.admin@demo.test")
    r = client.post(S(world["kaveri"]), headers=h,
                    json={"email": "extra@demo.test", "full_name": "Extra Staff"})
    assert r.status_code == 201, r.text
    u = r.json()["user"]
    assert u["role"] == "INSTITUTION_STAFF" and u["institution_id"] == world["kaveri"].id
    assert r.json()["temporary_password"]
    for extra in ({"role": "AICTE_ADMIN"}, {"institution_id": "x"}, {"is_active": False}):
        bad = client.post(S(world["kaveri"]), headers=h,
                          json={"email": "y@demo.test", "full_name": "Y"} | extra)
        assert bad.status_code == 422
    assert client.post(S(world["kaveri"]), headers=h, json={
        "email": "EXTRA@demo.test", "full_name": "Dup"}).status_code == 409


def test_institution_admin_is_refused_for_another_institution(client, login, db, world):
    h = login("kaveri.admin@demo.test")
    assert client.get(S(world["malabar"]), headers=h).status_code == 403
    r = client.post(S(world["malabar"]), headers=h, json={"email": "z@demo.test", "full_name": "Z"})
    assert r.status_code == 403
    assert "ACCESS.REFUSED" in actions(db)
    assert db.scalars(select(User).where(User.email == "z@demo.test")).first() is None


@pytest.mark.parametrize("who", ["officer.south@demo.test", "admin@demo.test",
                                 "kaveri.staff@demo.test", "verifier@demo.test"])
def test_only_the_institution_admin_manages_staff(client, login, db, world, who):
    assert client.get(S(world["kaveri"]), headers=login(who)).status_code == 403


def test_patch_and_deactivate_own_staff(client, login, db, world):
    h = login("kaveri.admin@demo.test")
    s = S(world["kaveri"])
    uid = world["users"]["inst_staff"].id
    r = client.patch(f"{s}/{uid}", headers=h, json={"full_name": "Renamed"})
    assert r.status_code == 200 and r.json()["full_name"] == "Renamed"
    assert client.patch(f"{s}/{uid}", headers=h, json={"role": "INSTITUTION_ADMIN"}).status_code == 422
    r = client.delete(f"{s}/{uid}", headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert db.get(User, uid) is not None  # deactivated, never deleted
    assert sign_in(client, "kaveri.staff@demo.test", PASSWORD) == 401
    r = client.patch(f"{s}/{uid}", headers=h, json={"is_active": True})
    assert r.status_code == 200 and r.json()["is_active"] is True
    assert "USER.DEACTIVATED" in actions(db)


def test_institution_admin_cannot_touch_admins_or_other_institutions_users(
        client, login, db, world):
    h = login("kaveri.admin@demo.test")
    s = S(world["kaveri"])
    assert client.delete(f"{s}/{world['users']['inst_admin'].id}", headers=h).status_code == 404
    assert client.delete(f"{s}/{world['users']['admin'].id}", headers=h).status_code == 404
    other = mal_staff(db, world)
    assert client.delete(f"{s}/{other.id}", headers=h).status_code == 404
    assert client.patch(f"{s}/{other.id}", headers=h, json={"full_name": "x"}).status_code == 404
    assert client.delete(f"{S(world['malabar'])}/{other.id}", headers=h).status_code == 403
    assert db.get(User, other.id).is_active


def test_institution_admin_can_reset_staff_password(client, login, db, world):
    h = login("kaveri.admin@demo.test")
    s = S(world["kaveri"])
    r = client.post(f"{s}/{world['users']['inst_staff'].id}/reset-password", headers=h)
    assert r.status_code == 200 and r.json()["temporary_password"]
    assert client.post(f"{s}/{world['users']['inst_admin'].id}/reset-password",
                       headers=h).status_code == 404
