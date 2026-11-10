from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"


def test_login_success_returns_both_tokens(client):
    r = client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD})
    assert r.status_code == 200
    assert {"access_token", "refresh_token"} <= set(r.json())


def test_wrong_password_and_unknown_email_look_identical(client):
    a = client.post(LOGIN, json={"email": "admin@demo.test", "password": "nope"})
    b = client.post(LOGIN, json={"email": "ghost@demo.test", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_inactive_user_cannot_login(client, db, world):
    world["users"]["admin"].is_active = False
    db.commit()
    r = client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD})
    assert r.status_code == 401


def test_login_is_rate_limited(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "login_max_attempts", 3)
    for _ in range(3):
        client.post(LOGIN, json={"email": "admin@demo.test", "password": "bad"})
    r = client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD})
    assert r.status_code == 429


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_the_user(client, login):
    r = client.get("/api/v1/auth/me", headers=login("kaveri.admin@demo.test"))
    assert r.status_code == 200
    assert r.json()["role"] == "INSTITUTION_ADMIN"
    assert "password_hash" not in r.json()


def test_refresh_gives_new_access_token(client):
    tokens = client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD}).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200 and "access_token" in r.json()


def test_access_token_cannot_be_used_to_refresh(client):
    tokens = client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD}).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


def test_language_can_be_changed_but_only_to_known_values(client, login):
    h = login("admin@demo.test")
    assert client.patch("/api/v1/auth/me", json={"language": "hi"}, headers=h).status_code == 200
    assert client.patch("/api/v1/auth/me", json={"language": "fr"}, headers=h).status_code == 422


def test_unknown_fields_are_rejected(client):
    r = client.post(LOGIN, json={"email": "a@b.c", "password": "x", "admin": True})
    assert r.status_code == 422


# --- refresh-token rotation (ADR-026) ---
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"


def _login(client):
    return client.post(LOGIN, json={"email": "admin@demo.test", "password": PASSWORD}).json()


def _refresh(client, token):
    return client.post(REFRESH, json={"refresh_token": token})


def _audits(db, action):
    from sqlalchemy import select

    from app.models.audit import AuditLog

    return db.scalars(select(AuditLog).where(AuditLog.action == action)).all()


def test_refresh_rotates_the_refresh_token(client):
    t = _login(client)
    r = _refresh(client, t["refresh_token"])
    assert r.status_code == 200
    assert r.json()["refresh_token"] != t["refresh_token"]


def test_reused_token_outside_grace_is_refused_and_revokes_the_family(client, db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "refresh_grace_seconds", 0)
    t = _login(client)
    new = _refresh(client, t["refresh_token"]).json()["refresh_token"]
    assert _refresh(client, t["refresh_token"]).status_code == 401  # thief replays the old one
    assert _refresh(client, new).status_code == 401  # the whole family is dead
    rows = _audits(db, "AUTH.REFRESH_REUSED")
    assert len(rows) == 1 and rows[0].entity_type == "user"


def test_replay_at_the_same_instant_is_refused_when_grace_is_zero(client, monkeypatch):
    from datetime import UTC, datetime

    from app.core.config import settings
    from app.services import sessions

    instant = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)  # clock frozen: first use and replay share it
    monkeypatch.setattr(sessions, "_now", lambda: instant)
    monkeypatch.setattr(settings, "refresh_grace_seconds", 0)
    t = _login(client)
    assert _refresh(client, t["refresh_token"]).status_code == 200
    assert _refresh(client, t["refresh_token"]).status_code == 401  # zero grace means no grace


def test_grace_window_accepts_previous_token_once(client, db):
    t = _login(client)
    first = _refresh(client, t["refresh_token"])
    assert first.status_code == 200
    again = _refresh(client, t["refresh_token"])  # second tab, same old token
    assert again.status_code == 200
    assert again.json()["refresh_token"] not in (t["refresh_token"], first.json()["refresh_token"])
    assert _refresh(client, first.json()["refresh_token"]).status_code == 200  # tab A still fine
    assert _refresh(client, t["refresh_token"]).status_code == 401  # third use: reuse
    assert len(_audits(db, "AUTH.REFRESH_REUSED")) == 1


def test_logout_revokes_the_family_and_is_audited(client, db):
    t = _login(client)
    assert client.post(LOGOUT, json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert _refresh(client, t["refresh_token"]).status_code == 401
    assert _audits(db, "AUTH.LOGOUT")


def test_logout_with_a_junk_token_is_harmless(client):
    assert client.post(LOGOUT, json={"refresh_token": "junk"}).status_code == 204


def test_expired_refresh_token_is_refused(client, world):
    from app.core.security import make_token

    tok = make_token(world["users"]["admin"].id, "refresh", minutes=-1)
    assert _refresh(client, tok).status_code == 401


def test_untracked_refresh_token_is_refused(client, world):
    from app.core.security import make_token

    assert _refresh(client, make_token(world["users"]["admin"].id, "refresh")).status_code == 401


def test_password_reset_revokes_all_sessions(client, login, world):
    t = _login(client)
    h = login("admin@demo.test")
    uid = world["users"]["admin"].id
    r = client.post(f"/api/v1/admin/users/{uid}/reset-password", headers=h)
    assert r.status_code == 200, r.text
    assert _refresh(client, t["refresh_token"]).status_code == 401
