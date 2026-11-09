"""Shared scene for the Phase 5 tests. Synthetic data only."""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.models.student import StudentRecord, ValidationFlag
from app.models.user import User
from tests.conftest import PASSWORD
from tests.ingest_helpers import ap, csv_bytes, programme, register, row, run


def add_user(db, email, role, inst):
    u = User(email=email, password_hash=hash_password(PASSWORD), full_name=email, role=role,
             institution_id=inst.id)
    db.add(u)
    db.commit()
    return u


def upload(db, inst, rows):
    register(db, rows)
    return run(db, inst, csv_bytes(rows))


def old_records(db, prog, n, cycle=2025, start=500):
    """Records of an earlier cycle written directly (no checks), for R10."""
    for i in range(n):
        db.add(StudentRecord(apaar_id=ap(start + i), name=f"Old {i}", dob=date(2000, 1, 1),
                             programme_id=prog.id, cycle_year=cycle, admission_date=date(2025, 7, 1),
                             admission_category="OPEN", status="valid"))
    db.commit()


def flags_of(db, rule=None):
    q = select(ValidationFlag)
    if rule:
        q = q.where(ValidationFlag.rule_code == rule)
    return db.scalars(q).all()


def dash_scene(db, world):
    """Kaveri: intake 4, 5 rows (R06 open, Excess). Malabar: intake 10, 3 rows, one bad ID and one
    missing ID (R02, R01 open: Alert). Northfield: intake 10, no upload (Clear, not submitted)."""
    programme(db, world["kaveri"], intake=4)
    programme(db, world["malabar"], name="B.Pharm", intake=10)
    programme(db, world["northfield"], name="B.Tech", intake=10)
    upload(db, world["kaveri"], [row(n) for n in range(1, 6)])
    upload(db, world["malabar"], [row(10), row(11, apaar_id="9999000001"), row(12, apaar_id="")])
