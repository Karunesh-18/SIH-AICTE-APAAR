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
