"""Impact preview for R08, R10 and R11: counts for looser and stricter values, nothing persisted."""
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.audit import AuditLog
from app.models.rules import RuleVersion
from app.models.student import StudentRecord, ValidationFlag
from app.services import rule_preview
from app.services.errors import Invalid
from tests.ingest_helpers import ap, programme
from tests.phase5_helpers import old_records


def rec(db, prog, n, name, dob=date(2002, 2, 2), status="valid", apaar=True):
    db.add(StudentRecord(apaar_id=ap(n) if apaar else "", name=name, dob=dob, programme_id=prog.id,
                         cycle_year=2026, admission_date=date(2026, 7, 1),
                         admission_category="OPEN", status=status))
    db.commit()


@pytest.fixture
def scene(db, world, rules):
    k = programme(db, world["kaveri"], name="MBA", intake=100)
    m = programme(db, world["malabar"], name="B.Pharm", intake=100)
    return k, m


def counts(p):
    return (p["current_count"], p["proposed_count"], p["added"], p["cleared"])


def test_r10_looser_and_stricter(db, world, scene):
    k, m = scene
    for n in (1, 2):
        rec(db, k, n, f"S {n}")
    old_records(db, programme(db, world["kaveri"], name="MBA", cycle=2025), 1)  # +100%
    for n in range(10, 21):
        rec(db, m, n, f"S {n}")
    old_records(db, programme(db, world["malabar"], name="B.Pharm", cycle=2025), 10, start=600)  # +10%
    loose = rule_preview.preview(db, "R10", {"jump_pct": 150})
    assert counts(loose) == (1, 0, 0, 1) and loose["cycle"] == 2026
    assert loose["cleared_examples"][0]["institution"] == world["kaveri"].name
    assert loose["cleared_examples"][0]["rise_pct"] == 100.0
    strict = rule_preview.preview(db, "R10", {"jump_pct": 5})
    assert counts(strict) == (1, 2, 1, 0)
    assert {r["name"]: (r["current"], r["proposed"]) for r in strict["by_institution"]} == {
        world["kaveri"].name: (1, 1), world["malabar"].name: (0, 1)}


def test_r11_looser_and_stricter(db, world, scene):
    k, m = scene
    rec(db, k, 1, "A")
    rec(db, k, 2, "B", status="pending_apaar", apaar=False)  # 50%
    for n in range(10, 20):
        rec(db, m, n, f"S {n}", status="pending_apaar" if n == 10 else "valid")  # 10%
    assert counts(rule_preview.preview(db, "R11", {"pending_pct": 60})) == (1, 0, 0, 1)
    assert counts(rule_preview.preview(db, "R11", {"pending_pct": 5})) == (1, 2, 1, 0)


def test_r08_looser_and_stricter(db, world, scene):
    k, m = scene
    d2 = date(2003, 3, 3)
    rec(db, k, 1, "Priyanka Deshmukh")
    rec(db, m, 2, "Priyanka Deshmuk")  # 0.94, across institutions
    rec(db, k, 3, "Meera Iyer", dob=d2)
    rec(db, k, 4, "Meera Iyers", dob=d2)  # 0.90
    rec(db, k, 5, "Rahul Sharma", dob=date(2004, 4, 4))
    rec(db, k, 6, "Rahul Sharna", dob=date(2004, 4, 4))  # 0.67
    assert counts(rule_preview.preview(db, "R08", {})) == (2, 2, 0, 0)
    strict = rule_preview.preview(db, "R08", {"threshold": 0.92})
    assert counts(strict) == (2, 1, 0, 1)
    ex = strict["cleared_examples"][0]
    assert ex["institutions"] == [world["kaveri"].name] and "XXXX" in ex["ids"]
    assert "Meera" not in str(strict) and "Priyanka" not in str(strict)
    loose = rule_preview.preview(db, "R08", {"threshold": 0.6})
    assert counts(loose) == (2, 3, 1, 0)
    row = next(r for r in loose["by_institution"] if r["name"] == world["malabar"].name)
    assert (row["current"], row["proposed"]) == (1, 1)


def test_preview_persists_nothing_and_leaves_rule_unchanged(db, world, scene):
    k, _ = scene
    for n in (1, 2):
        rec(db, k, n, f"S {n}")
    old_records(db, programme(db, world["kaveri"], name="MBA", cycle=2025), 1)

    def n(t):
        return db.scalar(select(func.count()).select_from(t))

    before = (n(ValidationFlag), n(AuditLog), n(RuleVersion))
    assert rule_preview.preview(db, "R10", {"jump_pct": 1})["proposed_count"] == 1
    db.rollback()
    assert (n(ValidationFlag), n(AuditLog), n(RuleVersion)) == before
    v = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == "R10")).one()
    assert v.is_active and v.params == {"jump_pct": 25}


def test_unsupported_code_is_invalid(db, rules):
    with pytest.raises(Invalid, match="R08, R10, R11"):
        rule_preview.preview(db, "R02", {})


def test_api_admin_ok_unsupported_422_and_others_403(client, login, db, world, scene):
    admin, officer = login("admin@demo.test"), login("officer.south@demo.test")
    r = client.post("/api/v1/admin/rules/R10/preview", json={"params": {"jump_pct": 1}},
                    headers=admin)
    assert r.status_code == 200 and r.json()["code"] == "R10"
    r = client.post("/api/v1/admin/rules/R02/preview", json={"params": {}}, headers=admin)
    assert r.status_code == 422 and "R08, R10, R11" in r.json()["detail"]
    assert client.post("/api/v1/admin/rules/R10/preview", json={"params": {}},
                       headers=officer).status_code == 403
