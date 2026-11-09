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


def test_narmada_near_duplicate_pair_raises_exactly_one_r08(demo):
    flags = demo.scalars(select(ValidationFlag).where(ValidationFlag.rule_code == "R08")).all()
    assert len(flags) == 1
    f = flags[0]
    assert demo.get(Institution, f.institution_id).name == "Narmada School of Management"
    assert f.evidence["score"] >= f.evidence["threshold"] == 0.85
    assert {f.evidence["a"]["name"], f.evidence["b"]["name"]} == {
        "Priyanka Deshmukh", "Priyanka Deshmuk"}


def test_narmada_pair_is_only_an_r08_not_registry_noise(demo):
    n = demo.scalars(select(Institution).where(
        Institution.name == "Narmada School of Management")).one()
    codes = [f.rule_code for f in demo.scalars(select(ValidationFlag).where(
        ValidationFlag.institution_id == n.id))]
    assert codes == ["R08"]  # the registry holds the same names the file carries


def test_refuses_to_run_twice(demo):
    with pytest.raises(RuntimeError):
        seed_demo_flags(demo)
