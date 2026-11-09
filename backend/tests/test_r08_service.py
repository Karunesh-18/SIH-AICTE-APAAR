"""R08 through the pipeline: arrival, recheck after a correction, masking in the API."""
import pytest
from sqlalchemy import select

from app.models.student import FlagRecord, ValidationFlag
from tests.ingest_helpers import csv_bytes, programme, register, row, run

DOB = "2002-02-02"


@pytest.fixture
def two(db, world, rules):
    programme(db, world["kaveri"], intake=10)
    programme(db, world["malabar"], intake=10)
    return world["kaveri"], world["malabar"]


def r08(db):
    return db.scalars(select(ValidationFlag).where(ValidationFlag.rule_code == "R08")).all()


def pair(first="Priyanka Deshmukh", second="Priyanka Deshmuk", **kw2):
    return [row(1, name=first, dob=DOB), row(2, name=second, dob=DOB, **kw2)]


def test_pair_inside_one_upload_raises_exactly_one_flag(db, two):
    k, _ = two
    rows = pair()
    register(db, rows)
    run(db, k, csv_bytes(rows))
    (f,) = r08(db)
    assert f.reason_key == "near_duplicate" and f.state == "open"
    assert f.evidence["score"] >= 0.85 and f.evidence["threshold"] == 0.85
    assert "XXXX XXXX 0001" in f.reason and "XXXX XXXX 0002" in f.reason
    assert "Priyanka" not in f.reason  # names stay out of the stored sentence
    recs = db.scalars(select(FlagRecord.record_id).where(FlagRecord.flag_id == f.id)).all()
    assert len(recs) == 2


def test_other_institution_in_the_same_cycle_is_compared(db, two):
    k, m = two
    ka = [row(1, name="Priyanka Deshmukh", dob=DOB)]
    register(db, ka)
    run(db, k, csv_bytes(ka))
    assert r08(db) == []
    mb = [row(2, name="Priyanka Deshmuk", dob=DOB)]
    register(db, mb)
    run(db, m, csv_bytes(mb))
    (f,) = r08(db)
    assert f.institution_id == m.id  # raised on the upload that brought the second record
    assert f.evidence["b"]["institution"] == k.name or f.evidence["a"]["institution"] == k.name
    linked = db.scalars(select(FlagRecord.record_id).where(FlagRecord.flag_id == f.id)).all()
    assert len(linked) == 1  # the other institution's record is evidence, not linked


def test_same_id_or_other_cycle_or_other_dob_is_not_flagged(db, two):
    k, _ = two
    programme(db, k, name="MBA2", intake=10, cycle=2025)
    rows = [row(1, name="Priyanka Deshmukh", dob=DOB),
            row(2, name="Priyanka Deshmuk", dob="2002-02-03")]
    register(db, rows)
    run(db, k, csv_bytes(rows))
    assert r08(db) == []


def test_missing_id_side_is_still_compared(db, two):
    k, _ = two
    rows = [row(1, name="Priyanka Deshmukh", dob=DOB), row(2, name="Priyanka Deshmuk", dob=DOB,
                                                           apaar_id="")]
    register(db, rows)
    run(db, k, csv_bytes(rows))
    assert len(r08(db)) == 1


def test_a_correction_does_not_raise_the_pair_again(client, login, db, two):
    k, _ = two
    rows = [row(1, name="Priyanka Deshmukh", dob=DOB),
            row(2, name="Priyanka Deshmuk", dob=DOB, apaar_id="")]
    register(db, rows)
    run(db, k, csv_bytes(rows))
    from app.models.student import StudentRecord
    rec = db.scalars(select(StudentRecord).where(StudentRecord.apaar_id.is_(None))).one()
    from tests.ingest_helpers import ap
    register(db, [row(7, name="Priyanka Deshmuk", dob=DOB)])
    r = client.patch(f"/api/v1/records/{rec.id}", headers=login("kaveri.admin@demo.test"),
                     json={"apaar_id": ap(7)})
    assert r.status_code == 200, r.text
    assert len(r08(db)) == 1


def test_dismissed_pair_stays_dismissed_after_a_correction(client, login, db, two):
    k, _ = two
    rows = [row(1, name="Priyanka Deshmukh", dob=DOB),
            row(2, name="Priyanka Deshmuk", dob=DOB, apaar_id="")]
    register(db, rows)
    run(db, k, csv_bytes(rows))
    (f,) = r08(db)
    off = login("officer.south@demo.test")
    assert client.post(f"/api/v1/flags/{f.id}/dismiss", headers=off,
                       json={"note": "different students"}).status_code == 200
    from app.models.student import StudentRecord
    from tests.ingest_helpers import ap
    rec = db.scalars(select(StudentRecord).where(StudentRecord.apaar_id.is_(None))).one()
    register(db, [row(7, name="Priyanka Deshmuk", dob=DOB)])
    client.patch(f"/api/v1/records/{rec.id}", headers=login("kaveri.admin@demo.test"),
                 json={"apaar_id": ap(7)})
    assert len(r08(db)) == 1


def test_evidence_names_are_masked_for_the_other_institution(client, login, db, two):
    k, m = two
    ka = [row(1, name="Priyanka Deshmukh", dob=DOB)]
    register(db, ka)
    run(db, k, csv_bytes(ka))
    mb = [row(2, name="Priyanka Deshmuk", dob=DOB)]
    register(db, mb)
    run(db, m, csv_bytes(mb))
    (f,) = r08(db)
    from app.core.security import hash_password
    from app.models.user import User
    from tests.conftest import PASSWORD
    db.add(User(email="malabar.admin@demo.test", password_hash=hash_password(PASSWORD),
                full_name="m", role="INSTITUTION_ADMIN", institution_id=m.id))
    db.commit()
    inst = client.get(f"/api/v1/flags/{f.id}", headers=login("malabar.admin@demo.test")).json()
    sides = {inst["evidence"]["a"]["institution_id"]: inst["evidence"]["a"],
             inst["evidence"]["b"]["institution_id"]: inst["evidence"]["b"]}
    assert sides[m.id]["name"] == "Priyanka Deshmuk"
    assert sides[k.id]["name"] == "P******* D*******"
    admin = client.get(f"/api/v1/flags/{f.id}", headers=login("admin@demo.test")).json()
    assert {admin["evidence"]["a"]["name"], admin["evidence"]["b"]["name"]} == {
        "Priyanka Deshmukh", "Priyanka Deshmuk"}
