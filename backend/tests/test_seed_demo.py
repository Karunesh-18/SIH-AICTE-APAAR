"""python -m app.seed --demo: reset, base seed, flags, windows and verification in one command."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core import clock
from app.db.base import Base
from app.models.consent import Consent, Verifier
from app.models.org import Institution
from app.models.student import FlagRecord, StudentRecord, Upload, ValidationFlag
from app.models.windows import SubmissionWindow
from app.seed import DEMO_PASSWORD, main, seed_demo


@pytest.fixture(autouse=True)
def _clock():
    clock.set_offset(0)
    yield
    clock.set_offset(0)


def fresh():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def fingerprint(db) -> dict:
    """Everything that should be identical between two runs (ids and timestamps excluded)."""
    inst = {i.id: i.name for i in db.scalars(select(Institution))}
    flags = sorted(
        (inst[f.institution_id], f.rule_code, f.reason_key, f.state,
         tuple(sorted(r for (r,) in db.execute(
             select(StudentRecord.row_number).join(
                 FlagRecord, FlagRecord.record_id == StudentRecord.id)
             .where(FlagRecord.flag_id == f.id)))),
         f.reason)
        for f in db.scalars(select(ValidationFlag)))
    records = sorted((inst[u.institution_id], r.row_number, r.apaar_id, r.name, str(r.dob), r.status,
                      r.is_current)
                     for r, u in db.execute(select(StudentRecord, Upload).join(
                         Upload, StudentRecord.upload_id == Upload.id)))
    return {"flags": flags, "records": records,
            "consents": sorted((c.apaar_id, tuple(c.purposes), c.withdrawn_at is None)
                               for c in db.scalars(select(Consent)))}


def test_demo_runs_on_an_empty_database():
    with fresh()() as db:
        seed_demo(db)
        assert db.scalar(select(func.count()).select_from(Institution)) == 15
        assert db.scalar(select(func.count()).select_from(ValidationFlag)) > 0
        assert db.scalar(select(func.count()).select_from(SubmissionWindow)) == 1
        assert db.scalar(select(func.count()).select_from(Verifier)) == 2
        assert {u.status for u in db.scalars(select(Upload))} == {"DONE"}


def test_demo_resets_a_database_that_already_has_data():
    with fresh()() as db:
        seed_demo(db)
        first = fingerprint(db)
        seed_demo(db)
        assert fingerprint(db) == first


def test_demo_is_deterministic_across_databases():
    a, b = fresh(), fresh()
    with a() as da, b() as dbb:
        seed_demo(da)
        seed_demo(dbb)
        assert fingerprint(da) == fingerprint(dbb)


def test_demo_puts_the_clock_back_to_now():
    clock.set_offset(5 * 86400)
    with fresh()() as db:
        seed_demo(db)
    assert clock.get_offset_seconds() == 0


def test_cli_demo_flag_runs_the_whole_chain(capsys):
    factory = fresh()
    main(["--demo"], factory)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Verifier)) == 2
    assert DEMO_PASSWORD in capsys.readouterr().out


def test_dashboards_and_reports_agree_on_the_demo_data():
    from app.db.session import get_db, get_session_factory
    from app.main import create_app

    factory = fresh()
    with factory() as db:
        seed_demo(db)
        app = create_app()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_session_factory] = lambda: lambda: db
        c = TestClient(app)
        tok = c.post("/api/v1/auth/login", json={"email": "admin@demo.test",
                                                 "password": DEMO_PASSWORD}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        dash = c.get("/api/v1/dashboards/aicte", headers=h).json()
        rows = dash["institutions"]
        enrol = c.get("/api/v1/reports/enrolment_vs_intake", headers=h).json()["rows"]
        cats = c.get("/api/v1/reports/category_counts", headers=h).json()["rows"]
        pend = c.get("/api/v1/reports/pending_apaar_share", headers=h).json()
        by_inst = c.get("/api/v1/reports/enrolment_vs_intake?group_by=institution",
                        headers=h).json()["rows"]

        tiles = dash["tiles"]
        assert tiles["records"] == sum(r["enrolled"] for r in rows) == sum(
            r["enrolled"] for r in enrol) == sum(r["records"] for r in cats)
        assert tiles["open_flags"] == sum(r["open_flags"] for r in rows)
        assert tiles["open_flags"] == c.get("/api/v1/flags?limit=200", headers=h).json()["total"] \
            - sum(1 for f in c.get("/api/v1/flags?limit=200", headers=h).json()["items"]
                  if f["state"] in ("resolved", "dismissed"))
        assert {r["institution"]: r["enrolled"] for r in by_inst if r["enrolled"]} == {
            r["name"]: r["enrolled"] for r in rows if r["enrolled"]}
        assert pend["total"]["total"] == tiles["records"]
        assert tiles["institutions"] == 15
        k = next(r for r in rows if r["name"] == "Kaveri Valley College")
        assert k["state"] == "Excess" and k["flags"] == {"R04": 1, "R06": 1, "R07": 1}
