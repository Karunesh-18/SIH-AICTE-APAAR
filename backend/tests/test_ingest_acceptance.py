"""Phase 3 acceptance: the seeded demonstration cases, uploaded as files, raise exactly the flags
the idea document promises. The seed supplies the data, the registry and the rules."""
import csv
import io

import pytest
from sqlalchemy import delete, select

from app.models.org import Institution
from app.models.student import (
    FlagEvent,
    FlagRecord,
    StudentRecord,
    Upload,
    ValidationFlag,
)
from app.seed import seed
from app.services import ingest

COLS = ["apaar_id", "name", "dob", "admission_date", "admission_category"]


@pytest.fixture
def demo(db):
    """Seed, turn each institution's seeded rows into CSV bytes, then clear the raw records."""
    seed(db)
    files = {}
    for inst in db.scalars(select(Institution)):
        recs = db.scalars(select(StudentRecord).join(Upload, StudentRecord.upload_id == Upload.id)
                          .where(Upload.institution_id == inst.id)
                          .order_by(StudentRecord.row_number)).all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(COLS)
        for r in recs:
            w.writerow([r.apaar_id or "", r.name, r.dob.isoformat(), r.admission_date.isoformat(),
                        r.admission_category])
        files[inst.name] = (inst, buf.getvalue().encode("utf-8"))
    for model in (FlagEvent, FlagRecord, ValidationFlag, StudentRecord, Upload):
        db.execute(delete(model))
    db.commit()
    return files


def go(db, demo, name):
    inst, data = demo[name]
    return ingest.ingest(db, actor=None, institution_id=inst.id, cycle_year=2026, data=data)


def flags_of(db, up):
    return db.scalars(select(ValidationFlag).where(ValidationFlag.upload_id == up.id)
                      .order_by(ValidationFlag.rule_code)).all()


def rows_of(db, flag):
    return sorted(db.scalars(select(StudentRecord.row_number).join(
        FlagRecord, FlagRecord.record_id == StudentRecord.id)
        .where(FlagRecord.flag_id == flag.id)).all())


def test_kaveri_exactly_three_flags_covering_eight_rows(db, demo):
    up = go(db, demo, "Kaveri Valley College")
    assert (up.status, up.row_count) == ("DONE", 132)
    r04, r06, r07 = flags_of(db, up)
    assert [f.rule_code for f in (r04, r06, r07)] == ["R04", "R06", "R07"]
    assert rows_of(db, r04) == [41, 97]
    assert (r06.evidence["allowed"], r06.evidence["actual"], r06.evidence["excess"]) == (126, 132, 6)
    assert len(rows_of(db, r06)) == 6
    assert r07.reason_key == "admission_after_cycle" and rows_of(db, r07) == [60]
    touched = {n for f in (r04, r06, r07) for n in rows_of(db, f)}
    assert len(touched) == 8 and up.flagged_count == 8 and up.accepted_count == 132
    current = db.scalars(select(StudentRecord).where(StudentRecord.is_current)).all()
    assert len(current) == 131  # row 97 is stored, not current (ADR-012)


def test_malabar_forty_of_forty_no_flags(db, demo):
    up = go(db, demo, "Malabar Pharmacy College")
    assert flags_of(db, up) == [] and up.flagged_count == 0
    assert {r.status for r in db.scalars(select(StudentRecord))} == {"valid"}


def test_sahyadri_one_r02_one_r01_nothing_else_held(db, demo):
    up = go(db, demo, "Sahyadri Engineering College")
    assert [f.rule_code for f in flags_of(db, up)] == ["R01", "R02"]
    assert up.flagged_count == 2 and up.accepted_count == 30
    by = {}
    for r in db.scalars(select(StudentRecord)):
        by.setdefault(r.status, []).append(r.row_number)
    assert by["pending_apaar"] == [14] and by["flagged"] == [7] and len(by["valid"]) == 28


def test_northfield_sharing_an_id_with_kaveri_gets_r05(db, demo):
    go(db, demo, "Kaveri Valley College")
    up = go(db, demo, "Northfield Institute")
    (f,) = flags_of(db, up)
    assert f.rule_code == "R05" and rows_of(db, f) == [5]
    assert f.evidence["elsewhere"][0]["institution"] == "Kaveri Valley College"
