from app.core.config import settings


def test_tamper_then_verify_reports_the_edited_row(client, login):
    h = login("admin@demo.test")
    assert client.post("/api/v1/admin/audit/verify", headers=h).json()["ok"] is True
    tampered = client.post("/api/v1/admin/dev/tamper-audit", headers=h).json()["tampered_id"]
    r = client.post("/api/v1/admin/audit/verify", headers=h).json()
    assert r["ok"] is False and r["first_broken_id"] == tampered


def test_tamper_endpoint_is_off_outside_demo_mode(client, login, monkeypatch):
    h = login("admin@demo.test")
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.post("/api/v1/admin/dev/tamper-audit", headers=h).status_code == 404


def test_clock_reports_demo_mode(client, login, monkeypatch):
    h = login("admin@demo.test")
    assert client.get("/api/v1/admin/clock", headers=h).json()["demo_mode"] is True
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/api/v1/admin/clock", headers=h).json()["demo_mode"] is False
