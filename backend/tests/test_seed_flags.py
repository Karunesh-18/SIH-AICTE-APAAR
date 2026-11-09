"""seed_demo_flags runs the real pipeline over the seeded rows, so dashboards have real flags."""
import pytest
from sqlalchemy import func, select

from app.models.org import Institution
from app.models.student import FlagRecord, StudentRecord, Upload, ValidationFlag
from app.seed import seed, seed_demo_flags


@pytest.fixture
def demo(db):
    seed(db)
    assert db.scalar(select(func.count()).select_from(ValidationFlag)) == 0  # default unchanged
    seed_demo_flags(db)
    return db


def test_kaveri_three_flags_covering_eight_rows(demo):
    k = demo.scalars(select(Institution).where(Institution.name == "Kaveri Valley College")).one()
    flags = demo.scalars(select(ValidationFlag).where(ValidationFlag.institution_id == k.id)).all()
    assert sorted(f.rule_code for f in flags) == ["R04", "R06", "R07"]
    rows = {r for (r,) in demo.execute(
        select(StudentRecord.row_number).join(FlagRecord, FlagRecord.record_id == StudentRecord.id)
        .where(FlagRecord.flag_id.in_([f.id for f in flags])))}
    assert len(rows) == 8


def test_other_demo_cases_and_uploads_done(demo):
    codes = sorted(f.rule_code for f in demo.scalars(select(ValidationFlag)))
    assert codes.count("R05") == 1 and codes.count("R02") == 1 and "R01" in codes
    assert {u.status for u in demo.scalars(select(Upload))} == {"DONE"}
    assert demo.scalar(select(func.count()).select_from(Upload)) == 15


def test_refuses_to_run_twice(demo):
    with pytest.raises(RuntimeError):
        seed_demo_flags(demo)
