"""Consent ledger and the object scope around it. A consent belongs to a student; the institution
that holds that student's current record (or AICTE) may record, withdraw and read it."""
from datetime import timedelta

from sqlalchemy import false, select
from sqlalchemy.orm import Session

from app.core import clock
from app.domain.apaar import mask, normalize
from app.models.consent import Consent
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.org import Institution, Programme
from app.models.student import StudentRecord
from app.models.user import User
from app.services import audit
from app.services.access import officer_region_ids
from app.services.errors import Conflict, Forbidden, Invalid, NotFound

MAX_VALID_DAYS = 3 * 366  # a consent cannot run for decades


def _current():
    return (select(StudentRecord, Programme).join(Programme, Programme.id == StudentRecord.programme_id)
            .where(StudentRecord.is_current, StudentRecord.status != "withdrawn"))


def current_record(db: Session, apaar: str | None):
    """(record, programme) for the newest current, non-withdrawn record, or None."""
    if not apaar:
        return None
    row = db.execute(_current().where(StudentRecord.apaar_id == apaar).order_by(
        StudentRecord.cycle_year.desc(), StudentRecord.created_at.desc()).limit(1)).first()
    return tuple(row) if row else None


def holds_student(db: Session, institution_id: str | None, apaar: str) -> bool:
    return institution_id is not None and db.execute(
        _current().where(StudentRecord.apaar_id == apaar,
                         Programme.institution_id == institution_id).limit(1)).first() is not None


def student_scope(db: Session, user: User):
    """None means every student; otherwise a select of the APAAR IDs the user may see."""
    if user.role == Role.AICTE_ADMIN:
        return None
    q = select(StudentRecord.apaar_id).join(Programme, Programme.id == StudentRecord.programme_id).where(
        StudentRecord.is_current, StudentRecord.status != "withdrawn",
        StudentRecord.apaar_id.is_not(None))
    if user.role == Role.AICTE_OFFICER:
        return q.join(Institution, Institution.id == Programme.institution_id).where(
            Institution.region_id.in_(officer_region_ids(db, user)))
    if user.role in INSTITUTION_ROLES:
        return q.where(Programme.institution_id == user.institution_id)
    return q.where(false())


def can_see_unmasked(db: Session, user: User, apaar: str) -> bool:
    return user.role in AICTE_ROLES or holds_student(db, user.institution_id, apaar)


def out(db: Session, user: User, c: Consent) -> dict:
    return {"id": c.id, "apaar_id": c.apaar_id if can_see_unmasked(db, user, c.apaar_id)
            else mask(c.apaar_id), "purposes": c.purposes, "fields": c.fields, "source": c.source,
            "given_at": c.given_at, "expires_at": c.expires_at, "withdrawn_at": c.withdrawn_at}


def record(db: Session, user: User, *, apaar_id: str, purposes: list, fields: list, source: str,
           expires_at) -> Consent:
    apaar = normalize(apaar_id)
    now = clock.now()
    if expires_at <= now or expires_at > now + timedelta(days=MAX_VALID_DAYS):
        raise Invalid("expires_at must be in the future and within three years")
    # An institution gets the same refusal for another institution's student and for an unknown
    # one, so this endpoint cannot be used to find out which IDs exist.
    if user.role in INSTITUTION_ROLES:
        if not holds_student(db, user.institution_id, apaar or ""):
            raise Forbidden("This student is not at your institution")
    elif current_record(db, apaar) is None:
        raise NotFound("Student not found")
    c = Consent(apaar_id=apaar, purposes=sorted(set(purposes)), fields=sorted(set(fields)),
                source=source, given_at=now, expires_at=expires_at, recorded_by=user.id)
    db.add(c)
    db.flush()
    audit.append(db, actor_id=user.id, actor_role=user.role, action="CONSENT.RECORDED",
                 entity_type="consent", entity_id=c.id,
                 after={"apaar_id": mask(apaar), "purposes": c.purposes, "fields": c.fields,
                        "source": source, "expires_at": expires_at.isoformat()})
    return c


def withdraw(db: Session, user: User, consent_id: str) -> Consent:
    c = db.get(Consent, consent_id)
    if c is None:
        raise NotFound("Consent not found")
    if user.role != Role.AICTE_ADMIN and not (
            user.role in INSTITUTION_ROLES and holds_student(db, user.institution_id, c.apaar_id)):
        raise Forbidden("This consent is outside your scope")
    if c.withdrawn_at is not None:
        raise Conflict("Already withdrawn")
    c.withdrawn_at = clock.now()
    audit.append(db, actor_id=user.id, actor_role=user.role, action="CONSENT.WITHDRAWN",
                 entity_type="consent", entity_id=c.id,
                 after={"apaar_id": mask(c.apaar_id), "withdrawn_at": c.withdrawn_at.isoformat()})
    return c


def list_scoped(db: Session, user: User, apaar: str | None, limit: int, offset: int):
    q = select(Consent)
    if (scope := student_scope(db, user)) is not None:
        q = q.where(Consent.apaar_id.in_(scope))
    if apaar:  # outside scope simply returns nothing: no oracle for "does this ID exist"
        q = q.where(Consent.apaar_id == normalize(apaar))
    return db.scalars(q.order_by(Consent.created_at.desc()).limit(limit).offset(offset)).all()
