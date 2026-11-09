"""Ingestion and validation at the service level: records, versions, flags, counts, audit."""
import pytest
from sqlalchemy import select

from app.adapters.registry import MockRegistry
from app.domain.rules import RegistryInfo
from app.models.audit import AuditLog
from app.models.notify import Notification
from app.models.rules import RuleVersion
from app.models.student import (
    FlagEvent,
    FlagRecord,
    StudentRecord,
    Upload,
    ValidationFlag,
)
from app.services import audit
from tests.ingest_helpers import ap, csv_bytes, json_bytes, programme, register, row, run


@pytest.fixture
def kav(db, world, rules):
    programme(db, world["kaveri"], intake=10, seats=0)
    return world["kaveri"]


def flags(db, upload=None):
    q = select(ValidationFlag).order_by(ValidationFlag.rule_code)
    if upload is not None:
        q = q.where(ValidationFlag.upload_id == upload.id)
    return db.scalars(q).all()


def rows_of(db, flag):
    nums = db.scalars(select(StudentRecord.row_number).join(
        FlagRecord, FlagRecord.record_id == StudentRecord.id).where(
        FlagRecord.flag_id == flag.id)).all()
    return sorted(nums)


def test_registry_adapter_reads_registry_entry(db):
    from datetime import date

    from app.models.student import RegistryEntry

    db.add(RegistryEntry(apaar_id=ap(1), name="Asha", dob=date(2000, 1, 1)))
    db.commit()
    reg = MockRegistry(db)
    assert reg.lookup(ap(1)) == RegistryInfo(name="Asha", dob=date(2000, 1, 1))
    assert reg.lookup(ap(2)) is None


def test_clean_upload_is_all_valid_and_done(db, kav):
    data = [row(n) for n in range(1, 6)]
    register(db, data)
    up = run(db, kav, csv_bytes(data))
    assert (up.status, up.row_count, up.accepted_count, up.flagged_count) == ("DONE", 5, 5, 0)
    recs = db.scalars(select(StudentRecord)).all()
    assert len(recs) == 5 and {r.status for r in recs} == {"valid"} and all(r.is_current for r in recs)
    assert flags(db) == []


# name, row overrides, rule, reason_key, record status. Registry knows the clean version of each row.
CASES = [
    ("R01", {"apaar_id": ""}, "R01", "id_missing", "pending_apaar"),
    ("R02", {"apaar_id": "99990000001"}, "R02", "id_format", "flagged"),
    ("R03-unknown", {"apaar_id": "999900009999"}, "R03", "registry_not_found", "flagged"),
    ("R03-name", {"name": "Completely Different"}, "R03", "registry_name_differs", "flagged"),
    ("R03-dob", {"dob": "2002-02-02"}, "R03", "registry_dob_differs", "flagged"),
    ("R07-future", {"admission_date": "2027-07-01"}, "R07", "admission_after_cycle", "flagged"),
    ("R07-dob", {"admission_date": "2000-01-01"}, "R07", "dob_after_admission", "flagged"),
    ("R07-name", {"name": ""}, "R07", "name_missing", "flagged"),
    ("R07-category", {"admission_category": ""}, "R07", "category_missing", "flagged"),
    ("R07-dob-missing", {"dob": ""}, "R07", "dob_missing", "flagged"),
]


@pytest.mark.parametrize("label,over,rule,key,status", CASES, ids=[c[0] for c in CASES])
def test_each_rule_raises_one_flag_for_its_row_only(db, kav, label, over, rule, key, status):
    clean = [row(n) for n in range(1, 4)]
    register(db, clean)
    sent = [clean[0], row(2, **over), clean[2]]
    up = run(db, kav, csv_bytes(sent))
    got = flags(db, up)
    assert [(f.rule_code, f.reason_key) for f in got] == [(rule, key)]
    assert rows_of(db, got[0]) == [2]
    rec = db.scalars(select(StudentRecord).where(StudentRecord.row_number == 2)).one()
    assert rec.status == status
    assert (up.accepted_count, up.flagged_count, up.status) == (3, 1, "DONE")
    assert {r.status for r in db.scalars(select(StudentRecord).where(
        StudentRecord.row_number != 2))} == {"valid"}


def test_unparseable_fields_are_stored_with_placeholders_and_flagged_not_rejected(db, kav):
    up = run(db, kav, csv_bytes([row(1, dob="", admission_date="garbage", name="")]))
    assert up.status == "DONE"
    keys = {f.reason_key for f in flags(db, up)}
    assert keys & {"name_missing", "dob_missing", "admission_date_missing"}
    assert db.scalars(select(StudentRecord)).one().status == "flagged"


def test_r04_duplicate_keeps_first_row_current_and_lists_both_rows(db, kav):
    data = [row(1), row(2), row(1, admission_date="2026-08-01")]
    register(db, data)
    up = run(db, kav, csv_bytes(data))
    f = [x for x in flags(db, up) if x.rule_code == "R04"]
    assert len(f) == 1 and rows_of(db, f[0]) == [1, 3] and f[0].evidence["count"] == 2
    first, _, later = db.scalars(select(StudentRecord).order_by(StudentRecord.row_number)).all()
    assert first.is_current and not later.is_current
    assert first.status == later.status == "flagged"
    assert up.flagged_count == 2


def test_r06_intake_cap_lists_excess_rows_with_numbers(db, world, rules):
    programme(db, world["kaveri"], intake=3, seats=1)
    data = [row(n, admission_date=f"2026-07-{n:02d}") for n in range(1, 7)]
    register(db, data)
    up = run(db, world["kaveri"], csv_bytes(data))
    (f,) = flags(db, up)
    assert f.rule_code == "R06" and rows_of(db, f) == [5, 6]
    assert f.evidence["allowed"] == 4 and f.evidence["actual"] == 6 and f.evidence["excess"] == 2
    assert "4" in f.reason and "6" in f.reason  # numbers in the reason text
    assert up.flagged_count == 2


def test_r05_flags_same_id_at_another_institution_with_masked_id(db, world, rules):
    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    shared = [row(1), row(2)]
    register(db, shared)
    run(db, world["kaveri"], csv_bytes(shared))
    up = run(db, world["northfield"], csv_bytes([row(1), row(3)]))
    (f,) = [x for x in flags(db, up) if x.rule_code == "R05"]
    assert rows_of(db, f) == [1]
    other = f.evidence["elsewhere"][0]
    assert other["institution"] == "Kaveri Valley College" and other["programme"] == "MBA"
    assert ap(1) not in str(f.evidence) and ap(1) not in f.reason
    assert f.institution_id == world["northfield"].id


def test_r05_ignores_withdrawn_records(db, world, rules):
    programme(db, world["kaveri"])
    programme(db, world["northfield"], name="B.Tech")
    register(db, [row(1)])
    run(db, world["kaveri"], csv_bytes([row(1)]))
    db.scalars(select(StudentRecord)).one().status = "withdrawn"
    db.commit()
    up = run(db, world["northfield"], csv_bytes([row(1)]))
    assert [f for f in flags(db, up) if f.rule_code == "R05"] == []


def test_r05_ignores_own_institution_reupload(db, kav):
    register(db, [row(1)])
    run(db, kav, csv_bytes([row(1)]))
    up2 = run(db, kav, csv_bytes([row(1)]))
    assert [f for f in flags(db, up2) if f.rule_code == "R05"] == []


def test_r03_uses_the_registry_adapter_given(db, kav):
    class Empty:
        def lookup(self, apaar_id):
            return None

    up = run(db, kav, csv_bytes([row(1)]), registry=Empty())
    assert [f.reason_key for f in flags(db, up)] == ["registry_not_found"]


def test_flag_snapshots_rule_version_and_renders_message_with_params(db, kav):
    up = run(db, kav, csv_bytes([row(1, apaar_id="123")]))
    (f,) = [x for x in flags(db, up) if x.rule_code == "R02"]
    v = db.get(RuleVersion, f.rule_version_id)
    assert v.rule_code == "R02" and v.version_no == 1
    assert "12 digits" in f.reason and "Row" in f.reason and "123" in f.reason
    assert f.state == "open"
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == f.id)).one()
    assert (ev.from_state, ev.to_state) == (None, "raised")


def test_disabled_rule_is_skipped(db, kav):
    v = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == "R07")).one()
    v.enabled = False
    db.commit()
    up = run(db, kav, csv_bytes([row(1, admission_date="2027-07-01")]))
    assert [f.rule_code for f in flags(db, up) if f.rule_code == "R07"] == []


def test_rule_params_are_read_from_the_active_version(db, kav):
    v = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == "R02")).one()
    v.params = {"digits": 10, "checksum": "none"}
    db.commit()
    up = run(db, kav, csv_bytes([row(1, apaar_id="1234567890")]))
    assert [f for f in flags(db, up) if f.rule_code == "R02"] == []


def test_same_file_twice_makes_new_versions_not_copies(db, kav):
    data = csv_bytes([row(1), row(2)])
    register(db, [row(1), row(2)])
    up1 = run(db, kav, data)
    up2 = run(db, kav, data)
    assert up1.id != up2.id and up1.file_hash == up2.file_hash
    recs = db.scalars(select(StudentRecord).order_by(StudentRecord.apaar_id,
                                                     StudentRecord.version)).all()
    assert len(recs) == 4
    old, new = recs[0], recs[1]
    assert (old.version, old.is_current, new.version, new.is_current) == (1, False, 2, True)
    assert old.superseded_by == new.id and old.superseded_at is not None
    assert new.continues_record_id == old.id
    assert sum(r.is_current for r in recs) == 2


def test_rejected_uploads_store_nothing_but_the_upload_row(db, kav):
    for data, words in [(b"", "empty"), (b"apaar_id,name\n1,a\n", "dob"), (b"\xff\xfe\x00junk", "read")]:
        up = run(db, kav, data)
        assert up.status == "REJECTED" and words in up.error.lower()
        assert up.accepted_count == 0
    assert db.scalars(select(StudentRecord)).all() == []
    assert flags(db) == []
    assert len(db.scalars(select(Upload)).all()) == 3


def test_unknown_programme_name_rejects_the_upload(db, kav):
    up = run(db, kav, csv_bytes([row(1, programme="Nope")], cols=[
        "apaar_id", "name", "dob", "admission_date", "admission_category", "programme"]))
    assert up.status == "REJECTED" and "Nope" in up.error


def test_programme_column_picks_among_several(db, world, rules):
    programme(db, world["kaveri"], name="MBA")
    programme(db, world["kaveri"], name="PGDM")
    cols = ["apaar_id", "name", "dob", "admission_date", "admission_category", "programme"]
    up = run(db, world["kaveri"], csv_bytes([row(1, programme="pgdm"), row(2, programme="MBA")],
                                            cols=cols))
    assert up.status == "DONE"
    # several programmes and no column: ambiguous, so the upload is rejected with a message
    up = run(db, world["kaveri"], csv_bytes([row(3)]))
    assert up.status == "REJECTED" and "programme" in up.error.lower()


def test_json_batch_via_api_source(db, kav):
    up = run(db, kav, json_bytes({"students": [row(1)]}), source="API", fmt="api")
    assert up.status == "DONE" and up.source == "API" and up.format == "api"


def test_notifications_go_to_institution_users_and_region_officers_for_r06(db, world, rules):
    programme(db, world["kaveri"], intake=1, seats=0)
    register(db, [row(1), row(2)])
    run(db, world["kaveri"], csv_bytes([row(1), row(2)]))
    got = db.scalars(select(Notification).where(Notification.channel == "IN_APP")).all()
    who = {n.user_id for n in got}
    u = world["users"]
    assert {u["inst_admin"].id, u["inst_staff"].id, u["officer_south"].id} <= who
    assert u["admin"].id not in who


def test_clean_upload_notifies_institution_only(db, kav, world):
    register(db, [row(1)])
    run(db, kav, csv_bytes([row(1)]))
    who = {n.user_id for n in db.scalars(select(Notification).where(
        Notification.channel == "IN_APP"))}
    assert world["users"]["officer_south"].id not in who


def test_audit_chain_records_receipt_processing_and_flags(db, kav):
    up = run(db, kav, csv_bytes([row(1, apaar_id="")]))
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert "UPLOAD.RECEIVED" in actions and "UPLOAD.PROCESSED" in actions
    assert "FLAG.RAISED" in actions
    assert audit.verify(db)["ok"]
    assert up.status == "DONE"


def test_rejection_is_audited(db, kav):
    run(db, kav, b"")
    assert "UPLOAD.REJECTED" in [a.action for a in db.scalars(select(AuditLog))]


def test_devanagari_names_stored_and_not_flagged(db, kav):
    data = [row(1, name="अनिका शर्मा")]
    register(db, data)
    up = run(db, kav, csv_bytes(data, bom=True))
    assert flags(db, up) == []
    assert db.scalars(select(StudentRecord)).one().name == "अनिका शर्मा"
