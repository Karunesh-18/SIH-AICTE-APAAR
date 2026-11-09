"""The flag review queue. A flag moves through the state machine in domain/flags.py; every move
needs a note, writes a FlagEvent and an audit entry, and tells the institution. Advisory only:
nothing here changes a student record."""
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import Session

from app.core import clock
from app.db.session import uow
from app.domain import flags as machine
from app.models.enums import INSTITUTION_ROLES, Role
from app.models.org import Institution, Programme, Region
from app.models.rules import RuleVersion
from app.models.student import FlagEvent, FlagRecord, StudentRecord, ValidationFlag
from app.models.user import User
from app.services import audit, notify, validation
from app.services.access import can_access_institution, officer_region_ids


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class Conflict(Exception):
    pass


AUDIT_ACTION = {"review": "FLAG.REVIEWED", "resolve": "FLAG.RESOLVED", "dismiss": "FLAG.DISMISSED",
                "ask": "FLAG.ASKED", "reply": "FLAG.REPLIED", "link": "FLAG.LINKED"}
VERB = {"review": "is under review", "resolve": "was resolved", "dismiss": "was dismissed",
        "ask": "needs your answer", "link": "was resolved (records linked)"}


def _refuse(db: Session, user: User, flag_id: str) -> None:
    with uow(db):
        audit.append(db, actor_id=user.id, actor_role=user.role, action="ACCESS.REFUSED",
                     entity_type="validation_flag", entity_id=flag_id)


def list_flags(db: Session, user: User, *, state=None, rule=None, institution=None, region=None,
               age_days=None, limit=25, offset=0):
    """Scoped, filtered, paginated. Returns (rows of (flag, institution, record_count), total)."""
    q = select(ValidationFlag, Institution).join(
        Institution, ValidationFlag.institution_id == Institution.id)
    if user.role == Role.AICTE_OFFICER:
        q = q.where(Institution.region_id.in_(officer_region_ids(db, user)))
    elif user.role in INSTITUTION_ROLES:
        q = q.where(ValidationFlag.institution_id == user.institution_id)
    elif user.role != Role.AICTE_ADMIN:
        q = q.where(False)
    if state:
        q = q.where(ValidationFlag.state == state)
    if rule:
        q = q.where(ValidationFlag.rule_code == rule)
    if institution:
        q = q.where(ValidationFlag.institution_id == institution)
    if region:
        q = q.join(Region, Institution.region_id == Region.id).where(
            or_(Region.id == region, Region.code == region))
    if age_days is not None:
        q = q.where(ValidationFlag.created_at <= clock.now() - timedelta(days=age_days))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    page = db.execute(q.order_by(ValidationFlag.created_at.desc(), ValidationFlag.id)
                      .limit(limit).offset(offset)).all()
    counts = dict(db.execute(select(FlagRecord.flag_id, func.count()).where(
        FlagRecord.flag_id.in_([f.id for f, _ in page])).group_by(FlagRecord.flag_id)).all())
    return [(f, i, counts.get(f.id, 0)) for f, i in page], total


def _load(db: Session, user: User, flag_id: str) -> ValidationFlag:
    flag = db.get(ValidationFlag, flag_id)
    if flag is None:
        raise NotFound
    if not can_access_institution(db, user, db.get(Institution, flag.institution_id)):
        _refuse(db, user, flag.id)
        raise Forbidden
    return flag


def view(db: Session, user: User, flag_id: str) -> dict:
    """One flag in full. A single-record view is audited."""
    flag = _load(db, user, flag_id)
    with uow(db):
        audit.append(db, actor_id=user.id, actor_role=user.role, action="FLAG.VIEWED",
                     entity_type="validation_flag", entity_id=flag.id)
    records = db.execute(
        select(StudentRecord, Programme).join(Programme, StudentRecord.programme_id == Programme.id)
        .join(FlagRecord, FlagRecord.record_id == StudentRecord.id)
        .where(FlagRecord.flag_id == flag.id)
        .order_by(StudentRecord.row_number, StudentRecord.id)).all()
    events = db.execute(
        select(FlagEvent, User).outerjoin(User, FlagEvent.actor_id == User.id)
        .where(FlagEvent.flag_id == flag.id).order_by(FlagEvent.at, FlagEvent.id)).all()
    return {"flag": flag, "institution": db.get(Institution, flag.institution_id),
            "rule_version": db.get(RuleVersion, flag.rule_version_id),
            "records": records, "events": events}


def act(db: Session, user: User, flag_id: str, action: str, note: str,
        lock_version: int | None = None) -> ValidationFlag:
    flag = _load(db, user, flag_id)
    if (action == "reply") != (user.role in INSTITUTION_ROLES):
        _refuse(db, user, flag.id)  # officers do not reply for an institution, nor it for them
        raise Forbidden
    if lock_version is not None and lock_version != flag.lock_version:
        raise Conflict("Someone else changed this flag. Reload it and try again.")
    if action == "link" and flag.rule_code != "R08":
        raise Conflict("Linking applies to near-duplicate flags (R08) only.")
    try:
        target = machine.next_state(flag.state, action)
    except machine.InvalidTransition as e:
        raise Conflict(str(e)) from None
    before = flag.state
    event_note = f"Linked as the same student: {note}" if action == "link" else note
    try:
        with uow(db):
            flag.state = target
            if action == "review":
                flag.assignee_id = user.id
            db.add(FlagEvent(flag_id=flag.id, from_state=before, to_state=target,
                             actor_id=user.id, note=event_note, at=clock.now()))
            audit.append(db, actor_id=user.id, actor_role=user.role, action=AUDIT_ACTION[action],
                         entity_type="validation_flag", entity_id=flag.id,
                         before={"state": before}, after={"state": target, "note": note})
            _notify(db, flag, user, action, note)
            db.flush()
    except StaleDataError:
        raise Conflict("Someone else changed this flag. Reload it and try again.") from None
    return flag


def _notify(db: Session, flag: ValidationFlag, user: User, action: str, note: str) -> None:
    inst = db.get(Institution, flag.institution_id)
    if action == "reply":
        who = validation.region_officers(db, inst.region_id)
        if flag.assignee_id and flag.assignee_id not in {u.id for u in who}:
            who.append(db.get(User, flag.assignee_id))
        notify.enqueue(db, who, subject=f"Reply on {flag.rule_code} flag from {inst.name}",
                       body=f"{inst.name} replied: {note}",
                       related_type="validation_flag", related_id=flag.id)
    else:
        notify.enqueue(db, validation.institution_users(db, inst.id),
                       subject=f"{flag.rule_code} flag {VERB[action]}", body=note,
                       related_type="validation_flag", related_id=flag.id)

