"""Verifier registration and approval, and the versioned purpose policies."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.consent import FIELDS, PURPOSES, PurposePolicy, Verifier
from app.models.user import User
from app.services import audit
from app.services.errors import Conflict, NotFound


def register(db: Session, *, org_name, org_type, contact, email, password, requested_purposes):
    """Creates an inactive VERIFIER user and a PENDING verifier. Returns None when the email is
    already taken: the caller answers the same either way, so the endpoint reveals nothing."""
    email = email.strip().lower()
    pw_hash = hash_password(password)  # always hashed first, so timing does not show whether the email exists
    if db.scalars(select(User).where(User.email == email)).first():
        return None
    user = User(email=email, password_hash=pw_hash, full_name=contact[:120],
                role="VERIFIER", is_active=False)
    db.add(user)
    db.flush()
    v = Verifier(org_name=org_name, org_type=org_type, contact=contact, user_id=user.id,
                 requested_purposes=sorted(set(requested_purposes)))
    db.add(v)
    db.flush()
    audit.append(db, actor_id=None, actor_role="PUBLIC", action="VERIFIER.REGISTERED",
                 entity_type="verifier", entity_id=v.id,
                 after={"org_name": org_name, "org_type": org_type,
                        "requested_purposes": v.requested_purposes})
    return v


def decide(db: Session, admin: User, verifier_id: str, approve: bool, note: str) -> Verifier:
    v = db.get(Verifier, verifier_id)
    if v is None:
        raise NotFound("Verifier not found")
    if v.status != "PENDING":
        raise Conflict(f"Already {v.status.lower()}")
    v.status = "APPROVED" if approve else "REJECTED"
    v.decided_by, v.decision_note = admin.id, note
    db.get(User, v.user_id).is_active = approve
    audit.append(db, actor_id=admin.id, actor_role=admin.role,
                 action="VERIFIER.APPROVED" if approve else "VERIFIER.REJECTED",
                 entity_type="verifier", entity_id=v.id, before={"status": "PENDING"},
                 after={"status": v.status, "note": note})
    return v


def list_verifiers(db: Session, status: str | None):
    q = select(Verifier, User.email).join(User, User.id == Verifier.user_id)
    if status:
        q = q.where(Verifier.status == status)
    return db.execute(q.order_by(Verifier.created_at.desc())).all()


def active_policy(db: Session, purpose: str) -> PurposePolicy | None:
    return db.scalars(select(PurposePolicy).where(
        PurposePolicy.purpose == purpose, PurposePolicy.is_active)).first()


def active_policies(db: Session) -> list[PurposePolicy]:
    rows = {p.purpose: p for p in db.scalars(select(PurposePolicy).where(PurposePolicy.is_active))}
    return [rows[p] for p in PURPOSES if p in rows]


def set_policy(db: Session, admin: User, purpose: str, allowed_fields: list, note: str):
    """A change is a new version row; the previous one stays, inactive."""
    assert purpose in PURPOSES and set(allowed_fields) <= set(FIELDS)
    old = active_policy(db, purpose)
    top = db.scalar(select(func.max(PurposePolicy.version)).where(
        PurposePolicy.purpose == purpose)) or 0
    if old:
        old.is_active = False
        db.flush()
    new = PurposePolicy(purpose=purpose, allowed_fields=[f for f in FIELDS if f in allowed_fields],
                        version=top + 1, is_active=True, note=note, created_by=admin.id)
    db.add(new)
    db.flush()
    audit.append(db, actor_id=admin.id, actor_role=admin.role, action="POLICY.UPDATED",
                 entity_type="purpose_policy", entity_id=new.id,
                 before={"version": old.version, "allowed_fields": old.allowed_fields}
                 if old else None,
                 after={"purpose": purpose, "version": new.version,
                        "allowed_fields": new.allowed_fields, "note": note})
    return new
