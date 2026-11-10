"""Rule health: officers' treatment of each rule's flags, read-only and unaudited."""
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.test_review_api import act, flag, scene  # noqa: F401  (scene is a fixture)

URL = "/api/v1/admin/rules/health"


def by_code(client, h, qs=""):
    return {r["code"]: r for r in client.get(URL + qs, headers=h).json()}


def test_counts_share_and_median(client, login, db, world, scene):  # noqa: F811
    admin = login("admin@demo.test")
    before = by_code(client, admin)
    assert before["R02"]["raised"] == 1 and before["R02"]["open"] == 1
    assert before["R02"]["dismissed_share"] is None and before["R02"]["oldest_open_days"] < 0.01
    assert before["R05"]["raised"] == 0 and before["R05"]["median_days_to_close"] is None

    off = login("officer.south@demo.test")
    assert act(client, off, flag(db, world["kaveri"], "R02").id, "dismiss").status_code == 200
    assert act(client, off, flag(db, world["kaveri"], "R01").id, "resolve").status_code == 200
    out = by_code(client, admin)
    assert (out["R02"]["dismissed"], out["R02"]["open"], out["R02"]["dismissed_share"]) == (1, 0, 1.0)
    assert (out["R01"]["resolved"], out["R01"]["dismissed_share"]) == (1, 0.0)
    assert out["R02"]["median_days_to_close"] < 0.01 and out["R02"]["oldest_open_days"] is None
    assert out["R03"]["open"] == 1  # untouched
    assert by_code(client, admin, "?cycle=1999")["R02"]["raised"] == 0


def test_permissions_and_no_audit(client, login, db, world, scene):  # noqa: F811
    h = {w: login(w) for w in ("admin@demo.test", "officer.south@demo.test", "kaveri.admin@demo.test", "verifier@demo.test")}
    n = len(db.scalars(select(AuditLog)).all())
    assert client.get(URL, headers=h["admin@demo.test"]).status_code == 200
    for who in ("officer.south@demo.test", "kaveri.admin@demo.test", "verifier@demo.test"):
        assert client.get(URL, headers=h[who]).status_code == 403
    assert len(db.scalars(select(AuditLog)).all()) == n
