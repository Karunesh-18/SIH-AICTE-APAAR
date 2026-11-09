"""The one query layer behind dashboards and reports, so their numbers always match.

Counting rules (ADR-015): only current rows (is_current) that are not withdrawn count.
Open flag = any state except resolved and dismissed.
Institution state: Excess = enrolment above intake plus supernumerary, or an open R06 flag;
Alert = open flags but within the cap; Clear = neither. Scoped by the caller's role.
"""
from collections import defaultdict

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.enums import INSTITUTION_ROLES, Role
from app.models.org import Institution, Programme, Region
from app.models.student import StudentRecord, Upload, ValidationFlag
from app.models.user import User
from app.models.windows import SubmissionWindow
from app.services.access import officer_region_ids

CLOSED_STATES = ("resolved", "dismissed")
STATES = ("Clear", "Alert", "Excess")


def default_cycle(db: Session) -> int:
    return db.scalar(select(func.max(Programme.cycle_year))) or 0


def scoped_institutions(db: Session, user: User, *, region=None, type_=None,
                        institution_id=None) -> list[Institution]:
    q = select(Institution).order_by(Institution.name)
    if user.role == Role.AICTE_OFFICER:
        q = q.where(Institution.region_id.in_(officer_region_ids(db, user)))
    elif user.role in INSTITUTION_ROLES:
        q = q.where(Institution.id == user.institution_id)
    elif user.role != Role.AICTE_ADMIN:
        q = q.where(False)
    if region:
        q = q.join(Region, Institution.region_id == Region.id).where(
            (Region.code == region) | (Region.id == region))
    if type_:
        q = q.where(Institution.type == type_)
    if institution_id:
        q = q.where(Institution.id == institution_id)
    return list(db.scalars(q).unique())


def current_filters(cycle: int):
    return (StudentRecord.is_current, StudentRecord.status != "withdrawn",
            StudentRecord.cycle_year == cycle)


def programme_rows(db: Session, ids: list[str], cycle: int) -> list[dict]:
    """Per programme: enrolled, approved intake, allowed (intake plus supernumerary)."""
    counts = dict(db.execute(select(StudentRecord.programme_id, func.count()).where(
        *current_filters(cycle)).group_by(StudentRecord.programme_id)).all())
    q = (select(Programme, Institution).join(Institution, Programme.institution_id == Institution.id)
         .where(Programme.cycle_year == cycle, Programme.institution_id.in_(ids))
         .order_by(Institution.name, Programme.name))
    return [{"institution_id": i.id, "institution": i.name, "region": i.region.name,
             "institution_type": i.type, "programme": p.name, "level": p.level,
             "enrolled": counts.get(p.id, 0), "approved_intake": p.approved_intake,
             "allowed": p.approved_intake + p.supernumerary_seats} for p, i in db.execute(q)]


def open_flag_counts(db: Session, ids: list[str]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(dict)
    q = (select(ValidationFlag.institution_id, ValidationFlag.rule_code, func.count())
         .where(ValidationFlag.institution_id.in_(ids), ValidationFlag.state.not_in(CLOSED_STATES))
         .group_by(ValidationFlag.institution_id, ValidationFlag.rule_code))
    for inst, rule, n in db.execute(q):
        out[inst][rule] = n
    return out


def last_uploads(db: Session, ids: list[str], cycle: int) -> dict:
    return dict(db.execute(select(Upload.institution_id, func.max(Upload.created_at)).where(
        Upload.institution_id.in_(ids), Upload.cycle_year == cycle)
        .group_by(Upload.institution_id)).all())


def state_of(enrolled: int, allowed: int, flags: dict[str, int]) -> str:
    if enrolled > allowed or flags.get("R06"):
        return "Excess"
    return "Alert" if flags else "Clear"


def institution_table(db: Session, user: User, cycle: int, *, region=None, type_=None,
                      state=None) -> list[dict]:
    insts = scoped_institutions(db, user, region=region, type_=type_)
    ids = [i.id for i in insts]
    progs = programme_rows(db, ids, cycle)
    flags, uploads = open_flag_counts(db, ids), last_uploads(db, ids, cycle)
    rows = []
    for i in insts:
        mine = [p for p in progs if p["institution_id"] == i.id]
        enrolled, allowed = sum(p["enrolled"] for p in mine), sum(p["allowed"] for p in mine)
        f = flags.get(i.id, {})
        rows.append({"id": i.id, "name": i.name, "type": i.type, "region": i.region.name,
                     "region_code": i.region.code, "state": state_of(enrolled, allowed, f),
                     "enrolled": enrolled, "approved_intake": sum(p["approved_intake"] for p in mine),
                     "allowed": allowed, "flags": f, "open_flags": sum(f.values()),
                     "last_upload": uploads.get(i.id)})
    return [r for r in rows if not state or r["state"] == state]


def pending_share(db: Session, ids: list[str], cycle: int) -> dict:
    q = (select(func.count(), func.coalesce(func.sum(
        (StudentRecord.status == "pending_apaar").cast(Integer)), 0))
         .join(Programme, StudentRecord.programme_id == Programme.id)
         .where(*current_filters(cycle), Programme.institution_id.in_(ids)))
    total, pending = db.execute(q).one()
    return {"pending": pending, "total": total,
            "share_pct": round(pending * 100 / total, 1) if total else 0.0}


def aicte_tiles(rows: list[dict], share: dict) -> dict:
    return {"institutions": len(rows), "records": sum(r["enrolled"] for r in rows),
            "open_flags": sum(r["open_flags"] for r in rows),
            "excess": sum(r["state"] == "Excess" for r in rows),
            "alert": sum(r["state"] == "Alert" for r in rows),
            "pending_apaar_share": share["share_pct"]}


def flags_by_rule_month(db: Session, ids: list[str]) -> list[dict]:
    counts: dict[tuple, int] = defaultdict(int)
    for created, rule in db.execute(select(ValidationFlag.created_at, ValidationFlag.rule_code)
                                    .where(ValidationFlag.institution_id.in_(ids))):
        counts[(created.strftime("%Y-%m"), rule)] += 1
    return [{"month": m, "rule": r, "count": n} for (m, r), n in sorted(counts.items())]


def category_counts(db: Session, ids: list[str], cycle: int) -> list[dict]:
    q = (select(Institution.name, Programme.name, StudentRecord.admission_category, func.count(),
                func.sum(StudentRecord.nri.cast(Integer)),
                func.sum(StudentRecord.oci.cast(Integer)),
                func.sum(StudentRecord.fn.cast(Integer)))
         .join(Programme, StudentRecord.programme_id == Programme.id)
         .join(Institution, Programme.institution_id == Institution.id)
         .where(*current_filters(cycle), Programme.institution_id.in_(ids))
         .group_by(Institution.name, Programme.name, StudentRecord.admission_category)
         .order_by(Institution.name, Programme.name, StudentRecord.admission_category))
    return [{"institution": i, "programme": p, "category": c, "records": n, "nri": a or 0,
             "oci": b or 0, "foreign_national": d or 0} for i, p, c, n, a, b, d in db.execute(q)]


def window_for(db: Session, inst: Institution, cycle: int) -> SubmissionWindow | None:
    q = select(SubmissionWindow).where(
        SubmissionWindow.cycle_year == cycle,
        (SubmissionWindow.institution_type == inst.type) | SubmissionWindow.institution_type.is_(None))
    return db.scalars(q.order_by(SubmissionWindow.institution_type.is_(None))).first()


def submission_status(db: Session, insts: list[Institution], cycle: int) -> list[dict]:
    """First upload per institution against its window: not_submitted, late or on_time."""
    first = dict(db.execute(select(Upload.institution_id, func.min(Upload.created_at)).where(
        Upload.institution_id.in_([i.id for i in insts]), Upload.cycle_year == cycle)
        .group_by(Upload.institution_id)).all())
    out = []
    for i in insts:
        w, at = window_for(db, i, cycle), first.get(i.id)
        status = "not_submitted" if at is None else (
            "late" if w and at > w.closes_at else "on_time")
        out.append({"institution_id": i.id, "institution": i.name, "region": i.region.name,
                    "status": status, "first_upload": at, "closes_at": w.closes_at if w else None})
    return out


def duplicate_cases(db: Session, ids: list[str]) -> list[dict]:
    q = select(ValidationFlag, Institution).join(
        Institution, ValidationFlag.institution_id == Institution.id).where(
        ValidationFlag.rule_code.in_(("R05", "R08")), ValidationFlag.institution_id.in_(ids)
    ).order_by(ValidationFlag.created_at)
    return [{"institution": i.name, "rule": f.rule_code, "state": f.state,
             "apaar_id": f.evidence.get("apaar_id"),  # already masked when the flag was raised
             "raised": f.created_at.date().isoformat(),
             "resolved": f.updated_at.date().isoformat() if f.state in CLOSED_STATES else None}
            for f, i in db.execute(q)]
