"""Scheduled rules R09-R12. Rule-based and visible: each flag names its rule version and the
figures it used. Advisory only; an identical open flag is never raised twice."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.db.session import uow
from app.domain import rules_scheduled as S
from app.models.org import Institution, Programme
from app.models.student import FlagEvent, StudentRecord, Upload, ValidationFlag
from app.models.user import User
from app.models.windows import SubmissionWindow
from app.services import audit, metrics, notify, validation


def _enrolled_by_institution(db: Session, cycle: int) -> dict[str, int]:
    return dict(db.execute(select(Programme.institution_id, func.count()).join(
        StudentRecord, StudentRecord.programme_id == Programme.id).where(
        *metrics.current_filters(cycle)).group_by(Programme.institution_id)).all())


def _pending_by_institution(db: Session, cycle: int) -> dict[str, int]:
    return dict(db.execute(select(Programme.institution_id, func.count()).join(
        StudentRecord, StudentRecord.programme_id == Programme.id).where(
        *metrics.current_filters(cycle), StudentRecord.status == "pending_apaar")
        .group_by(Programme.institution_id)).all())


def _mix(db: Session, *where) -> dict[str, int]:
    return dict(db.execute(select(StudentRecord.admission_category, func.count()).where(
        *where).group_by(StudentRecord.admission_category)).all())


def _facts(db: Session, inst: Institution, cycle: int, window: SubmissionWindow):
    ups = db.scalars(select(Upload).where(Upload.institution_id == inst.id,
                                          Upload.cycle_year == cycle)).all()
    return [S.UploadFact(u.created_at, u.row_count, _mix(db, StudentRecord.upload_id == u.id,
                                                        StudentRecord.status != "withdrawn"))
            for u in ups if u.created_at <= window.closes_at]


def _earlier_mix(db: Session, inst: Institution, cycle: int) -> dict[str, int]:
    return _mix(db, StudentRecord.is_current, StudentRecord.status != "withdrawn",
                StudentRecord.cycle_year == cycle - 1, StudentRecord.programme_id.in_(
                    select(Programme.id).where(Programme.institution_id == inst.id)))


def _already_open(db: Session, inst_id: str, rule: str, cycle: int) -> bool:
    return any(f.evidence.get("cycle_year") == cycle for f in db.scalars(select(ValidationFlag).where(
        ValidationFlag.institution_id == inst_id, ValidationFlag.rule_code == rule,
        ValidationFlag.state.not_in(metrics.CLOSED_STATES))))


def run_in_tx(db: Session, now, cycle: int, window: SubmissionWindow | None = None,
              actor: User | None = None, institutions: list[Institution] | None = None
              ) -> list[ValidationFlag]:
    """Inside the caller's transaction. R09 and R12 need a window; R10 and R11 do not."""
    versions = validation._active_versions(db)
    insts = institutions if institutions is not None else list(db.scalars(
        select(Institution).where(Institution.status == "ACTIVE")).unique())
    enrolled, pending = _enrolled_by_institution(db, cycle), _pending_by_institution(db, cycle)
    previous = _enrolled_by_institution(db, cycle - 1)
    submitted = {i for (i,) in db.execute(select(Upload.institution_id).where(
        Upload.cycle_year == cycle).distinct())}
    raised: list[ValidationFlag] = []
    for inst in insts:
        drafts = []
        if "R09" in versions and window is not None:
            d = S.r09_missing(submitted=inst.id in submitted, closed=now > window.closes_at,
                              closes_at=window.closes_at, params=versions["R09"].params)
            drafts += [d] if d else []
        if "R10" in versions:
            d = S.r10_jump(enrolled.get(inst.id, 0), previous.get(inst.id), versions["R10"].params)
            drafts += [d] if d else []
        if "R11" in versions:
            d = S.r11_pending(pending.get(inst.id, 0), enrolled.get(inst.id, 0),
                              versions["R11"].params)
            drafts += [d] if d else []
        if "R12" in versions and window is not None:
            d = S.r12_bulk(_facts(db, inst, cycle, window), window.closes_at,
                           _earlier_mix(db, inst, cycle), versions["R12"].params)
            drafts += [d] if d else []
        for d in drafts:
            if _already_open(db, inst.id, d.rule, cycle):
                continue
            d.evidence = {"cycle_year": cycle, **d.evidence}
            v = versions[d.rule]
            msg = v.message_en.format_map(validation._Fmt({**v.params, **d.evidence}))
            f = ValidationFlag(rule_code=d.rule, rule_version_id=v.id, institution_id=inst.id,
                               reason_key=d.reason_key, state="open", evidence=d.evidence,
                               reason=f"{msg} {validation._evidence_text(d.evidence)}.")
            db.add(f)
            db.flush()
            db.add(FlagEvent(flag_id=f.id, from_state=None, to_state="raised",
                                        actor_id=None, note=f"{d.rule} v{v.version_no}",
                                        at=clock.now()))
            audit.append(db, actor_id=actor.id if actor else None,
                         actor_role=actor.role if actor else "SYSTEM", action="FLAG.RAISED",
                         entity_type="validation_flag", entity_id=f.id,
                         after={"rule": d.rule, "rule_version_id": v.id,
                                "reason_key": d.reason_key, "cycle_year": cycle})
            notify.enqueue(db, validation.region_officers(db, inst.region_id),
                           subject=f"{d.rule} flagged at {inst.name}", body=f"{inst.name}: {f.reason}",
                           related_type="validation_flag", related_id=f.id)
            raised.append(f)
    return raised


def run(db: Session, now, cycle: int, window: SubmissionWindow | None = None,
        actor: User | None = None) -> list[ValidationFlag]:
    with uow(db):
        return run_in_tx(db, now, cycle, window, actor,
                         _window_institutions(db, window) if window else None)


def _window_institutions(db: Session, window: SubmissionWindow) -> list[Institution]:
    q = select(Institution).where(Institution.status == "ACTIVE")
    if window.institution_type:
        q = q.where(Institution.type == window.institution_type)
    return list(db.scalars(q).unique())


def run_all(db: Session, now, actor: User | None = None) -> list[ValidationFlag]:
    """Every window's cycle; with no window, the current cycle for R10 and R11."""
    wins = list(db.scalars(select(SubmissionWindow)))
    out: list[ValidationFlag] = []
    for w in wins or [None]:
        out += run(db, now, w.cycle_year if w else metrics.default_cycle(db), w, actor)
    if actor:
        with uow(db):
            audit.append(db, actor_id=actor.id, actor_role=actor.role, action="ANOMALY.RUN",
                         entity_type="anomaly", entity_id="scheduled",
                         after={"raised": len(out)})
    return out

