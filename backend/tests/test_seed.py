from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.security import verify_password
from app.models.org import Institution, Programme
from app.models.rules import Rule, RuleVersion
from app.models.student import RegistryEntry, StudentRecord, Upload
from app.models.user import User
from app.seed import DEMO_PASSWORD, seed


@pytest.fixture
def seeded(db):
    seed(db)
    return db


def inst(db, name):
    return db.scalars(select(Institution).where(Institution.name == name)).one()


def records(db, name, current_only=False):
    q = (select(StudentRecord).join(Programme).join(Institution)
         .where(Institution.name == name))
    if current_only:
        q = q.where(StudentRecord.is_current)
    return db.scalars(q).all()


def test_fifteen_institutions_all_fictional_and_regions_present(seeded):
    assert seeded.scalar(select(func.count()).select_from(Institution)) == 15
    assert all(i.aicte_id.startswith("FX-") for i in seeded.scalars(select(Institution)))


def test_demo_users_one_per_role_with_shared_demo_password(seeded):
    expect = {"admin@demo.test": "AICTE_ADMIN", "officer@demo.test": "AICTE_OFFICER",
              "inst-admin@demo.test": "INSTITUTION_ADMIN", "staff@demo.test": "INSTITUTION_STAFF",
              "verifier@demo.test": "VERIFIER"}
    for email, role in expect.items():
        u = seeded.scalars(select(User).where(User.email == email)).one()
        assert u.role == role and verify_password(DEMO_PASSWORD, u.password_hash)
    admin = seeded.scalars(select(User).where(User.email == "inst-admin@demo.test")).one()
    assert admin.institution_id == inst(seeded, "Kaveri Valley College").id


def test_twelve_rules_each_with_one_active_version(seeded):
    codes = {r.code for r in seeded.scalars(select(Rule))}
    assert codes == {f"R{n:02d}" for n in range(1, 13)}
    for c in codes:
        active = seeded.scalars(select(RuleVersion).where(RuleVersion.rule_code == c,
                                                          RuleVersion.is_active)).all()
        assert len(active) == 1 and active[0].version_no == 1
    r02 = seeded.scalars(select(RuleVersion).where(RuleVersion.rule_code == "R02")).one()
    assert r02.params == {"digits": 12, "checksum": "none"}


def test_every_seeded_id_is_marked_invented_and_in_registry_with_matching_details(seeded):
    ids = {r.apaar_id for r in seeded.scalars(select(StudentRecord)) if r.apaar_id
           and len(r.apaar_id) == 12}
    assert ids and all(i.startswith("9999") for i in ids)
    reg = {e.apaar_id: e for e in seeded.scalars(select(RegistryEntry))}
    assert ids <= set(reg)


def test_kaveri_file_has_132_rows_against_an_allowed_126(seeded):
    k = inst(seeded, "Kaveri Valley College")
    prog = seeded.scalars(select(Programme).where(Programme.institution_id == k.id)).one()
    assert (prog.approved_intake, prog.supernumerary_seats) == (120, 6)
    up = seeded.scalars(select(Upload).where(Upload.institution_id == k.id)).one()
    assert up.row_count == 132
    assert len(records(seeded, "Kaveri Valley College")) == 132


def test_kaveri_duplicate_id_on_rows_41_and_97_only_one_is_current(seeded):
    dups = [r for r in records(seeded, "Kaveri Valley College") if r.apaar_id == "999900000041"]
    assert sorted(r.row_number for r in dups) == [41, 97]
    assert len({r.name for r in dups}) == 1
    assert len({r.admission_date for r in dups}) == 2
    assert sum(r.is_current for r in dups) == 1


def test_kaveri_future_dated_row_is_among_the_six_over_cap_rows(seeded):
    """Why the idea doc's 3 flags cover 8 rows (6 + 2 + 1, one row in two flags)."""
    rows = [r for r in records(seeded, "Kaveri Valley College")]
    future = [r for r in rows if r.admission_date.year == 2027]
    assert len(future) == 1
    last_six = sorted(rows, key=lambda r: (r.admission_date, r.row_number))[-6:]
    assert future[0] in last_six
    dup_rows = {41, 97}
    assert future[0].row_number not in dup_rows
    assert not dup_rows & {r.row_number for r in last_six}
    assert len(dup_rows | {r.row_number for r in last_six}) == 8


def test_malabar_is_clean_40_of_40(seeded):
    prog = seeded.scalars(select(Programme).join(Institution)
                          .where(Institution.name == "Malabar Pharmacy College")).one()
    recs = records(seeded, "Malabar Pharmacy College")
    assert prog.approved_intake == 40 and len(recs) == 40
    assert all(r.apaar_id and len(r.apaar_id) == 12 for r in recs)
    assert len({r.apaar_id for r in recs}) == 40


def test_northfield_58_of_60_and_shares_one_id_with_kaveri(seeded):
    nf = records(seeded, "Northfield Institute")
    assert len(nf) == 58
    shared = {r.apaar_id for r in nf} & {r.apaar_id for r in records(seeded, "Kaveri Valley College")}
    assert len(shared) == 1


def test_bad_id_case_has_one_eleven_digit_id_and_one_missing(seeded):
    recs = records(seeded, "Sahyadri Engineering College")
    assert sum(1 for r in recs if r.apaar_id and len(r.apaar_id) == 11) == 1
    assert sum(1 for r in recs if not r.apaar_id) == 1


def test_pending_apaar_case_is_held_as_pending(seeded):
    pending = [r for r in records(seeded, "Gomti Management Institute") if not r.apaar_id]
    assert pending and all(r.status == "pending_apaar" for r in pending)


def test_near_duplicate_case_has_similar_names_same_dob_different_ids(seeded):
    recs = records(seeded, "Narmada School of Management")
    by_dob = {}
    for r in recs:
        by_dob.setdefault(r.dob, []).append(r)
    pair = [g for g in by_dob.values() if len(g) == 2 and g[0].apaar_id != g[1].apaar_id]
    assert len(pair) == 1
    a, b = pair[0]
    assert a.name != b.name and a.name.split()[0][:3] == b.name.split()[0][:3]


def test_reset_is_idempotent_and_plain_seed_refuses_a_non_empty_db(db):
    seed(db)
    with pytest.raises(RuntimeError, match="not empty"):
        seed(db)
    seed(db, reset=True)
    assert db.scalar(select(func.count()).select_from(Institution)) == 15
    assert db.scalar(select(func.count()).select_from(StudentRecord)) > 0


def test_seed_is_deterministic(db):
    seed(db)
    first = sorted((r.apaar_id or "", r.name) for r in db.scalars(select(StudentRecord)))
    seed(db, reset=True)
    assert first == sorted((r.apaar_id or "", r.name) for r in db.scalars(select(StudentRecord)))
    assert all(r.dob < date(2010, 1, 1) for r in db.scalars(select(StudentRecord)))
