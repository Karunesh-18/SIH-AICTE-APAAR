import pytest

from app.seed import seed_policies


@pytest.mark.parametrize("who", ["admin@demo.test", "verifier@demo.test", "kaveri.staff@demo.test"])
def test_any_signed_in_role_reads_policies(client, login, db, who):
    seed_policies(db)
    db.commit()
    r = client.get("/api/v1/policies", headers=login(who))
    assert r.status_code == 200
    body = r.json()
    assert {p["purpose"] for p in body["items"]} >= {"EMPLOYMENT"}
    assert "name" in body["fields"]
    assert "note" not in body["items"][0]  # read-only view: no admin notes


def test_policies_need_sign_in(client):
    assert client.get("/api/v1/policies").status_code == 401
