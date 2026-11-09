from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.org import Programme
from app.models.rules import Rule, RuleVersion
from app.models.student import (
    FlagEvent,
    FlagRecord,
    RegistryEntry,
    StudentRecord,
    Upload,
    ValidationFlag,
)


@pytest.fixture
def prog(db, world):
    p = Programme(institution_id=world["kaveri"].id, name="MBA", level="PG", cycle_year=2026,
                  approved_intake=120, supernumerary_seats=6)
    db.add(p)
    db.commit()
    return p


def rec(prog, apaar="999900000001", **kw):
    base = {"apaar_id": apaar, "name": "Test Student", "dob": date(2003, 1, 1), "programme_id": prog.id,
                "cycle_year": 2026, "year_of_study": 1, "admission_date": date(2026, 7, 1),
                "admission_category": "OPEN", "status": "submitted"}
    base.update(kw)
    return StudentRecord(**base)


def test_two_current_records_with_same_id_programme_cycle_are_rejected(db, prog):
    db.add(rec(prog))
    db.commit()
    db.add(rec(prog))
    with pytest.raises(IntegrityError):
        db.commit()


def test_superseded_record_does_not_block_a_new_current_one(db, prog):
    db.add(rec(prog, is_current=False))
    db.add(rec(prog, version=2))
    db.commit()
    assert len(db.scalars(select(StudentRecord)).all()) == 2


def test_same_id_in_another_programme_or_cycle_is_allowed(db, world, prog):
    other = Programme(institution_id=world["northfield"].id, name="BTech", level="UG",
                      cycle_year=2026, approved_intake=60)
    db.add(other)
    db.flush()
    db.add_all([rec(prog), rec(other), rec(prog, cycle_year=2025)])
    db.commit()


def test_many_records_without_an_id_are_allowed(db, prog):
    db.add_all([rec(prog, apaar=None, status="pending_apaar") for _ in range(3)])
    db.commit()


@pytest.mark.parametrize("field,value", [
    ("status", "approved"), ("year_of_study", 0), ("version", 0), ("admission_category", ""),
])
def test_bad_record_values_are_rejected(db, prog, field, value):
    db.add(rec(prog, **{field: value}))
    with pytest.raises(IntegrityError):
        db.commit()


def test_one_active_version_per_rule_and_unique_version_numbers(db):
    db.add(Rule(code="R01", scope="upload", title="ID missing"))
    db.flush()
    db.add(RuleVersion(rule_code="R01", version_no=1, enabled=True, params={}, message_en="m",
                       is_active=True))
    db.commit()
    db.add(RuleVersion(rule_code="R01", version_no=2, enabled=True, params={}, message_en="m",
                       is_active=True))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(RuleVersion(rule_code="R01", version_no=1, enabled=True, params={}, message_en="m",
                       is_active=False))
    with pytest.raises(IntegrityError):
        db.commit()


def test_rule_scope_is_constrained(db):
    db.add(Rule(code="R99", scope="whenever", title="x"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_flag_links_records_and_keeps_its_history(db, world, prog):
    r1 = rec(prog)
    db.add(r1)
    db.add(Rule(code="R04", scope="upload", title="dup"))
    db.flush()
    rv = RuleVersion(rule_code="R04", version_no=1, enabled=True, params={}, message_en="m",
                     is_active=True)
    up = Upload(institution_id=world["kaveri"].id, cycle_year=2026, source="FILE", format="csv",
                file_hash="a" * 64, row_count=1, status="DONE")
    db.add_all([rv, up])
    db.flush()
    f = ValidationFlag(rule_code="R04", rule_version_id=rv.id, institution_id=world["kaveri"].id,
                       upload_id=up.id, reason_key="dup_in_file", reason="x", evidence={"rows": [1]},
                       state="open")
    db.add(f)
    db.flush()
    db.add(FlagRecord(flag_id=f.id, record_id=r1.id))
    db.add(FlagEvent(flag_id=f.id, from_state=None, to_state="open", note="raised"))
    db.commit()
    db.add(FlagRecord(flag_id=f.id, record_id=r1.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_flag_state_is_constrained(db, world):
    db.add(ValidationFlag(rule_code="R01", rule_version_id="x", institution_id=world["kaveri"].id,
                          reason_key="k", reason="r", evidence={}, state="banished"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_registry_ids_are_unique(db):
    db.add(RegistryEntry(apaar_id="999900000001", name="A", dob=date(2003, 1, 1)))
    db.commit()
    db.add(RegistryEntry(apaar_id="999900000001", name="B", dob=date(2003, 1, 2)))
    with pytest.raises(IntegrityError):
        db.commit()
