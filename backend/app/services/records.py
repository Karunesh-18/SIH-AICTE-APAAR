"""Record corrections and withdrawals. A correction never edits a row: it adds the next version
(ADR-012 history), closes the flags that no longer describe the record and re-runs the row rules.
Withdrawn records stay current but count nowhere (ADR-015). Advisory only."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import MockRegistry, RegistryAdapter
from app.core import clock
from app.db.base import new_id
from app.db.session import uow
from app.domain import flags as machine
from app.domain.apaar import normalize
from app.models.org import Institution, Programme
from app.models.student import FlagEvent, FlagRecord, StudentRecord, ValidationFlag
from app.models.user import User
from app.services import audit, notify, validation
from app.services.access import can_access_institution
from app.services.errors import Conflict, Forbidden, Invalid, NotFound

FIELDS = ("apaar_id", "name", "dob", "year_of_study", "admission_date", "admission_category",
          "nri", "oci", "fn")
CLOSABLE = {"R01", "R02", "R03", "R05", "R07"}  # rules about one record's own fields


def _j(v):
    return v.isoformat() if isinstance(v, date) else v


def _load_for_write(db: Session, actor: User, record_id: str) -> tuple[StudentRecord, Programme]:
    rec = db.get(StudentRecord, record_id)
    if rec is None:
        raise NotFound
    prog = db.get(Programme, rec.programme_id)
    if not can_access_institution(db, actor, db.get(Institution, prog.institution_id)):
        with uow(db):
            audit.append(db, actor_id=actor.id, actor_role=actor.role, action="ACCESS.REFUSED",
                         entity_type="student_record", entity_id=rec.id)
        raise Forbidden
    if not rec.is_current:
        raise Conflict("This is an earlier version. Open the current version to change it.")
    if rec.status == "withdrawn":
        raise Conflict("This record is withdrawn.")
    return rec, prog


def correct(db: Session, actor: User, record_id: str, changes: dict,
            registry: RegistryAdapter | None = None) -> dict:
    old, prog = _load_for_write(db, actor, record_id)
    changes = {k: v for k, v in changes.items() if k in FIELDS}
    if "apaar_id" in changes:
        changes["apaar_id"] = normalize(changes["apaar_id"])
        if changes["apaar_id"] is None:
            raise Invalid("The APAAR ID cannot be cleared. Leave it out to keep it as it is.")
    diff = {k: v for k, v in changes.items() if getattr(old, k) != v}
    if not diff:
        raise Invalid("Nothing to change: the values are the same as the current version.")
    if diff.get("apaar_id") and db.scalar(select(StudentRecord.id).where(
            StudentRecord.is_current, StudentRecord.apaar_id == diff["apaar_id"],
            StudentRecord.programme_id == old.programme_id,
            StudentRecord.cycle_year == old.cycle_year, StudentRecord.id != old.id)):
        raise Conflict("Another current record in this programme already has that APAAR ID. "
                       "Withdraw or correct that record first.")
    registry = registry or MockRegistry(db)
    with uow(db):
        now = clock.now()
        old.is_current, old.superseded_at = False, now
        db.flush()  # free the one-current-record slot
        new = StudentRecord(
            id=new_id(), **{f: getattr(old, f) for f in FIELDS} | diff,
            programme_id=old.programme_id, cycle_year=old.cycle_year, version=old.version + 1,
            is_current=True, continues_record_id=old.id, upload_id=old.upload_id,
            row_number=old.row_number, consent_ref=old.consent_ref,
            consent_source=old.consent_source,
            status="pending_apaar" if old.apaar_id is None and "apaar_id" not in diff
            else "submitted")
        db.add(new)
        db.flush()
        old.superseded_by = new.id
        closed, carried = _close_stale(db, actor, old, new)
        raised = validation.recheck_record(db, new, prog, registry, actor)
        new.status = ("pending_apaar" if new.apaar_id is None
                      else "flagged" if raised or carried else "valid")
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="RECORD.CORRECTED",
                     entity_type="student_record", entity_id=old.id,
                     before={k: _j(getattr(old, k)) for k in diff},
                     after={k: _j(v) for k, v in diff.items()} | {
                         "new_record_id": new.id, "version": new.version,
                         "closed_flags": [f.id for f in closed],
                         "raised_flags": [f.id for f in raised]})
        inst = db.get(Institution, prog.institution_id)
        codes = sorted({f.rule_code for f in raised} & validation.OFFICER_RULES)
        if codes:
            notify.enqueue(db, validation.region_officers(db, inst.region_id),
                           subject=f"{', '.join(codes)} flagged at {inst.name}",
                           body=f"A correction at {inst.name} raised a new flag.",
                           related_type="student_record", related_id=new.id)
    notify.dispatch_now(db)
    return {"new": new, "old": old, "programme": prog, "closed": closed, "raised": raised}


def _close_stale(db: Session, actor: User, old: StudentRecord, new: StudentRecord):
    """Flags on the old version: close the ones about its own fields, carry the others over."""
    flags = db.scalars(select(ValidationFlag).join(
        FlagRecord, FlagRecord.flag_id == ValidationFlag.id).where(
        FlagRecord.record_id == old.id)).all()
    closed, carried = [], []
    for f in flags:
        if machine.is_terminal(f.state):
            continue
        if f.rule_code in CLOSABLE:
            note = ("R01 resolved by the system: the APAAR ID was supplied by a correction"
                    if f.rule_code == "R01" and old.apaar_id is None and new.apaar_id
                    else "superseded by correction")
            db.add(FlagEvent(flag_id=f.id, from_state=f.state, to_state="resolved",
                             actor_id=None, note=note, at=clock.now()))
            audit.append(db, actor_id=actor.id, actor_role=actor.role, action="FLAG.RESOLVED",
                         entity_type="validation_flag", entity_id=f.id,
                         before={"state": f.state}, after={"state": "resolved", "note": note,
                                                           "by": "system, on correction"})
            f.state = "resolved"
            closed.append(f)
        else:
            db.add(FlagRecord(flag_id=f.id, record_id=new.id))
            carried.append(f)
    db.flush()
    return closed, carried


def withdraw(db: Session, actor: User, record_id: str, reason: str) -> StudentRecord:
    rec, prog = _load_for_write(db, actor, record_id)
    with uow(db):
        before = rec.status
        rec.status, rec.withdrawn_reason = "withdrawn", reason
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="RECORD.WITHDRAWN",
                     entity_type="student_record", entity_id=rec.id,
                     before={"status": before}, after={"status": "withdrawn", "reason": reason})
        if rec.apaar_id:
            _tell_counterparts(db, rec, prog)
        db.flush()
    notify.dispatch_now(db)
    return rec


def _tell_counterparts(db: Session, rec: StudentRecord, prog: Programme) -> None:
    """Institutions holding an open R05 flag for the same student hear that this side withdrew.
    The flag itself stays open: an officer decides (demo case 4)."""
    inst = db.get(Institution, prog.institution_id)
    flags = db.scalars(select(ValidationFlag).join(
        FlagRecord, FlagRecord.flag_id == ValidationFlag.id).join(
        StudentRecord, FlagRecord.record_id == StudentRecord.id).where(
        ValidationFlag.rule_code == "R05", ValidationFlag.state.not_in(sorted(machine.TERMINAL)),
        StudentRecord.apaar_id == rec.apaar_id, StudentRecord.cycle_year == rec.cycle_year,
        ValidationFlag.institution_id != inst.id)).all()
    for f in flags:
        other = db.get(Institution, f.institution_id)
        notify.enqueue(db, validation.institution_users(db, other.id)
                       + validation.region_officers(db, other.region_id),
                       subject="Other institution withdrew a listed student",
                       body=f"{inst.name} marked its record withdrawn. An AICTE officer can now "
                            "review the flag.",
                       related_type="validation_flag", related_id=f.id)
