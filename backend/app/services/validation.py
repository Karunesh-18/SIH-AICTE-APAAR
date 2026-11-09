"""Run the active rules over one stored upload. Advisory only: it writes flags and routes them,
it never changes, rejects or penalises a record. Every flag names its rule version and its numbers."""
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import RegistryAdapter
from app.core import clock
from app.domain import rules as R
from app.domain.apaar import mask
from app.models.org import Institution, Programme
from app.models.rules import RuleVersion
from app.models.student import (
    FlagEvent,
    FlagRecord,
    StudentRecord,
    Upload,
    ValidationFlag,
)
from app.models.user import User, UserRegion
from app.services import audit, notify

OFFICER_RULES = {"R05", "R06"}


class _Fmt(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def actor_of(db: Session, up: Upload) -> dict:
    user = db.get(User, up.uploaded_by) if up.uploaded_by else None
    return {"actor_id": user.id if user else None, "actor_role": user.role if user else "API_KEY"}


def institution_users(db: Session, institution_id: str) -> list[User]:
    return list(db.scalars(select(User).where(User.institution_id == institution_id,
                                              User.is_active)))


def region_officers(db: Session, region_id: str) -> list[User]:
    return list(db.scalars(select(User).join(UserRegion, UserRegion.user_id == User.id).where(
        UserRegion.region_id == region_id, User.role == "AICTE_OFFICER", User.is_active)))


def _evidence_text(ev: dict) -> str:
    parts = []
    for k, v in ev.items():
        if k == "elsewhere":
            parts.append("also listed at " + "; ".join(
                f"{e['institution']} ({e['programme']}, admitted {e['admission_date']})" for e in v))
        elif k == "this":
            parts.append(f"here: {v['programme']}, admitted {v['admission_date']}")
        elif not isinstance(v, dict | list):
            parts.append(f"{k.replace('_', ' ')}: {v}")
    return "; ".join(parts)


def render_reason(version: RuleVersion, draft: R.FlagDraft) -> str:
    msg = version.message_en.format_map(_Fmt({**version.params, **draft.evidence}))
    rows = ", ".join(str(n) for n in draft.row_numbers)
    ev = _evidence_text(draft.evidence)
    return f"{msg} Row{'s' if len(draft.row_numbers) > 1 else ''} {rows}." + (f" {ev}." if ev else "")


def _active_versions(db: Session) -> dict[str, RuleVersion]:
    return {v.rule_code: v for v in db.scalars(select(RuleVersion).where(
        RuleVersion.is_active, RuleVersion.enabled))}


def _elsewhere(db: Session, cycle_year: int, institution_id: str, ids: set[str]) -> tuple[dict[str, list[dict]], set[str]]:
    """Other institutions' current, non-withdrawn records for the same cycle, by APAAR ID."""
    found: dict[str, list[dict]] = defaultdict(list)
    inst_ids: set[str] = set()
    if not ids:
        return found, inst_ids
    q = (select(StudentRecord, Programme, Institution)
         .join(Programme, StudentRecord.programme_id == Programme.id)
         .join(Institution, Programme.institution_id == Institution.id)
         .where(StudentRecord.is_current, StudentRecord.cycle_year == cycle_year,
                StudentRecord.status != "withdrawn", StudentRecord.apaar_id.in_(ids),
                Programme.institution_id != institution_id))
    for rec, prog, inst in db.execute(q):
        found[rec.apaar_id].append({"institution": inst.name, "programme": prog.name,
                                    "admission_date": rec.admission_date.isoformat()})
        inst_ids.add(inst.id)
    return found, inst_ids


def _r05(rows: list[R.Row], others: dict, prog: Programme) -> list[R.FlagDraft]:
    """R05 drafts with the APAAR ID masked and this institution's side of the story attached."""
    out = []
    for d in R.r05_two_institutions(rows, others):
        row = next(r for r in rows if r.row_number == d.row_numbers[0])
        d.evidence = {**d.evidence, "apaar_id": mask(d.evidence["apaar_id"]),
                      "this": {"programme": prog.name,
                               "admission_date": row.admission_date.isoformat()
                               if row.admission_date else None}}
        out.append(d)
    return out


def validate(db: Session, up: Upload, parsed: list[R.Row], records: dict[int, StudentRecord],
             prog_of: dict[int, Programme], registry: RegistryAdapter, *, superseded: int = 0) -> None:
    """Runs inside the caller's transaction (the ingest use case)."""
    versions = _active_versions(db)
    by_prog: dict[str, list[R.Row]] = defaultdict(list)
    for r in parsed:
        by_prog[prog_of[r.row_number].id].append(r)

    def active(code):
        return versions[code].params if code in versions else None

    drafts: list[R.FlagDraft] = []
    others, other_inst = _elsewhere(db, up.cycle_year, up.institution_id, {r.apaar_id for r in parsed if r.apaar_id}) \
        if "R05" in versions else ({}, set())
    for rows in by_prog.values():
        prog = prog_of[rows[0].row_number]
        info = R.ProgrammeInfo(prog.approved_intake, prog.supernumerary_seats)
        if (p := active("R01")) is not None:
            drafts += R.r01_missing_id(rows, p)
        if (p := active("R02")) is not None:
            drafts += R.r02_format(rows, p)
        if (p := active("R03")) is not None and p.get("registry_enabled", True):
            drafts += R.r03_registry(rows, p, registry.lookup)
        if (p := active("R04")) is not None:
            drafts += R.r04_duplicate_in_file(rows, p)
        if active("R05") is not None:
            drafts += _r05(rows, others, prog)
        if (p := active("R06")) is not None:
            drafts += R.r06_intake_cap(rows, info, p)
        if (p := active("R07")) is not None:
            drafts += R.r07_fields(rows, up.cycle_year, p)

    touched: set[int] = set()
    raised = []
    for d in drafts:
        raised.append(_persist(db, d, versions[d.rule], up.institution_id, up.id,
                               [records[n].id for n in d.row_numbers]))
        touched.update(d.row_numbers)

    for n, rec in records.items():
        rec.status = ("pending_apaar" if rec.apaar_id is None
                      else "flagged" if n in touched else "valid")
    up.accepted_count, up.flagged_count, up.status = len(records), len(touched), "DONE"
    db.flush()

    actor = actor_of(db, up)
    for f in raised:
        audit.append(db, **actor, action="FLAG.RAISED", entity_type="validation_flag",
                     entity_id=f.id, after={"rule": f.rule_code, "rule_version_id": f.rule_version_id,
                                            "reason_key": f.reason_key, "upload_id": up.id})
    # ponytail: one audit entry for the batch of record writes, not one per row
    audit.append(db, **actor, action="UPLOAD.PROCESSED", entity_type="upload", entity_id=up.id,
                 after={"row_count": up.row_count, "accepted": up.accepted_count,
                        "flagged": up.flagged_count, "flags": len(raised),
                        "records_superseded": superseded})

    inst = db.get(Institution, up.institution_id)
    summary = f"{up.row_count} rows received, {up.flagged_count} flagged for review."
    notify.enqueue(db, institution_users(db, up.institution_id), subject="Upload processed",
                   body=summary, related_type="upload", related_id=up.id)
    codes = sorted({f.rule_code for f in raised} & OFFICER_RULES)
    if codes:
        notify.enqueue(db, region_officers(db, inst.region_id),
                       subject=f"{', '.join(codes)} flagged at {inst.name}",
                       body=f"{inst.name}: {summary}", related_type="upload", related_id=up.id)
    if other_inst and any(f.rule_code == "R05" for f in raised):
        for oid in other_inst:
            notify.enqueue(db, institution_users(db, oid), subject="Student listed elsewhere",
                           body=f"{inst.name} lists a student who is also on your list for "
                                f"{up.cycle_year}. If the student transferred, mark one record withdrawn.",
                           related_type="upload", related_id=up.id)



def _persist(db: Session, d: R.FlagDraft, v: RuleVersion, institution_id: str,
             upload_id: str | None, record_ids: list[str]) -> ValidationFlag:
    flag = ValidationFlag(rule_code=d.rule, rule_version_id=v.id, institution_id=institution_id,
                          upload_id=upload_id, reason_key=d.reason_key, reason=render_reason(v, d),
                          evidence=d.evidence, state="open")
    db.add(flag)
    db.flush()
    for rid in record_ids:
        db.add(FlagRecord(flag_id=flag.id, record_id=rid))
    db.add(FlagEvent(flag_id=flag.id, from_state=None, to_state="raised", actor_id=None,
                     note=f"{d.rule} v{v.version_no}", at=clock.now()))
    return flag


def recheck_record(db: Session, rec: StudentRecord, prog: Programme, registry: RegistryAdapter,
                   actor: User) -> list[ValidationFlag]:
    """Row-level rules (R01, R02, R03, R05, R07) for one corrected record. Runs inside the
    caller's transaction. Aggregate rules (R04 in a file, R06 cap) are not re-run per record."""
    versions = _active_versions(db)
    placeholder = lambda d: None if d == date.min else d
    row = R.Row(row_number=rec.row_number or 1, apaar_id=rec.apaar_id, name=rec.name,
                dob=placeholder(rec.dob), admission_date=placeholder(rec.admission_date),
                admission_category=rec.admission_category)
    rows = [row]
    drafts: list[R.FlagDraft] = []
    if (v := versions.get("R01")) is not None:
        drafts += R.r01_missing_id(rows, v.params)
    if (v := versions.get("R02")) is not None:
        drafts += R.r02_format(rows, v.params)
    if (v := versions.get("R03")) is not None and v.params.get("registry_enabled", True):
        drafts += R.r03_registry(rows, v.params, registry.lookup)
    if "R05" in versions and rec.apaar_id:
        others, _ = _elsewhere(db, rec.cycle_year, prog.institution_id, {rec.apaar_id})
        drafts += _r05(rows, others, prog)
    if (v := versions.get("R07")) is not None:
        drafts += R.r07_fields(rows, rec.cycle_year, v.params)
    raised = [_persist(db, d, versions[d.rule], prog.institution_id, rec.upload_id, [rec.id])
              for d in drafts]
    for f in raised:
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="FLAG.RAISED",
                     entity_type="validation_flag", entity_id=f.id,
                     after={"rule": f.rule_code, "rule_version_id": f.rule_version_id,
                            "reason_key": f.reason_key, "record_id": rec.id})
    return raised
