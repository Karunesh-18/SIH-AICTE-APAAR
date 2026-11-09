"""User and staff management. Every change is audited (never with a password or hash). Accounts
are deactivated, never deleted, so the audit trail keeps pointing at a real user."""
import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import uow
from app.models.enums import INSTITUTION_ROLES, Role
from app.models.org import Institution, Region
from app.models.user import User, UserRegion
from app.services import audit, sessions
from app.services.errors import Conflict, Invalid, NotFound

MIN_PASSWORD = 10
DEMO_PASSWORDS = {"Demo@1234"}  # the published demo password; never allowed outside demo mode
MANAGED_ROLES = {r.value for r in Role if r is not Role.VERIFIER}  # verifiers self-register
INSTITUTION_ROLE_VALUES = {r.value for r in INSTITUTION_ROLES}


def check_password(pw: str) -> None:
    if len(pw) < MIN_PASSWORD:
        raise Invalid(f"The password must be at least {MIN_PASSWORD} characters.")
    if not settings.demo_mode and pw in DEMO_PASSWORDS:
        raise Invalid("That is the published demo password; choose another.")


def new_temporary_password() -> str:
    return secrets.token_urlsafe(12)  # 16 characters


def regions_of(db: Session, user_id: str) -> list[str]:
    return sorted(db.scalars(select(Region.code).join(
        UserRegion, UserRegion.region_id == Region.id).where(UserRegion.user_id == user_id)))


def out(db: Session, u: User) -> dict:
    inst = db.get(Institution, u.institution_id) if u.institution_id else None
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
            "institution_id": u.institution_id, "institution_name": inst.name if inst else None,
            "is_active": u.is_active, "language": u.language, "regions": regions_of(db, u.id)}


def _snapshot(db: Session, u: User) -> dict:
    o = out(db, u)
    return {k: o[k] for k in ("email", "full_name", "role", "institution_id", "is_active", "regions")}


def _region_ids(db: Session, regions: list[str]) -> list[str]:
    ids = []
    for ref in dict.fromkeys(regions):
        rid = db.scalar(select(Region.id).where(or_(Region.code == ref, Region.id == ref)))
        if rid is None:
            raise Invalid(f"Unknown region: {ref}")
        ids.append(rid)
    return ids


def _check_shape(db: Session, role: str, institution_id: str | None, regions: list[str]) -> None:
    if role in INSTITUTION_ROLE_VALUES:
        if not institution_id:
            raise Invalid("An institution is required for institution roles.")
        if db.get(Institution, institution_id) is None:
            raise Invalid("Unknown institution.")
    elif institution_id:
        raise Invalid("AICTE users do not belong to an institution.")
    if regions and role != Role.AICTE_OFFICER:
        raise Invalid("Regions apply to AICTE officers only.")


def _taken(db: Session, email: str) -> bool:
    return db.scalar(select(func.count()).select_from(User).where(
        func.lower(User.email) == email.lower())) > 0


def create(db: Session, actor: User, *, email: str, full_name: str, role: str,
           institution_id: str | None = None, regions: list[str] | None = None,
           password: str | None = None) -> tuple[User, str | None]:
    """Returns the user and the temporary password (None when the caller chose one)."""
    email = email.strip().lower()
    if role not in MANAGED_ROLES:
        raise Invalid("That role cannot be created here.")
    regions = regions or []
    _check_shape(db, role, institution_id, regions)
    region_ids = _region_ids(db, regions)
    if password is not None:
        check_password(password)
    if _taken(db, email):
        raise Conflict("That email is already in use.")
    temp = None if password else new_temporary_password()
    with uow(db):
        u = User(email=email, full_name=full_name.strip(), role=role,
                 institution_id=institution_id, password_hash=hash_password(password or temp))
        db.add(u)
        db.flush()
        db.add_all(UserRegion(user_id=u.id, region_id=r) for r in region_ids)
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="USER.CREATED",
                     entity_type="user", entity_id=u.id, after=_snapshot(db, u))
    return u, temp


def _get(db: Session, user_id: str, institution_id: str | None) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise NotFound("User not found")
    if institution_id is not None and (u.institution_id != institution_id
                                       or u.role != Role.INSTITUTION_STAFF):
        raise NotFound("User not found")  # an institution admin only ever sees its own staff
    return u


def _other_active_admins(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).select_from(User).where(
        User.role == Role.AICTE_ADMIN, User.is_active, User.id != user.id))


def update(db: Session, actor: User, user_id: str, changes: dict, *,
           institution_id: str | None = None) -> User:
    """changes may hold role, is_active, full_name, institution_id, regions (callers whitelist)."""
    u = _get(db, user_id, institution_id)
    new_role = changes.get("role", u.role)
    deactivating = changes.get("is_active") is False and u.is_active
    if u.id == actor.id and (deactivating or new_role != u.role):
        raise Conflict("You cannot deactivate yourself or change your own role.")
    if new_role != u.role and Role.VERIFIER in (u.role, new_role):
        raise Conflict("Verifier accounts are managed on the verifier screens.")
    if u.role == Role.AICTE_ADMIN and u.is_active and (deactivating or new_role != u.role) \
            and _other_active_admins(db, u) == 0:
        raise Conflict("This is the last active AICTE admin.")
    inst = changes.get("institution_id", u.institution_id if new_role in INSTITUTION_ROLE_VALUES
                       else None)
    keep_regions = u.role == Role.AICTE_OFFICER
    regions = changes.get("regions", regions_of(db, u.id) if keep_regions else [])
    if new_role != Role.AICTE_OFFICER:
        if changes.get("regions"):
            raise Invalid("Regions apply to AICTE officers only.")
        regions = []
    _check_shape(db, new_role, inst, regions)
    region_ids = _region_ids(db, regions)
    with uow(db):
        before = _snapshot(db, u)
        for k in ("full_name", "is_active"):
            if k in changes:
                setattr(u, k, changes[k])
        u.role, u.institution_id = new_role, inst
        for r in db.scalars(select(UserRegion).where(UserRegion.user_id == u.id)):
            db.delete(r)
        db.flush()
        db.add_all(UserRegion(user_id=u.id, region_id=r) for r in region_ids)
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role,
                     action="USER.DEACTIVATED" if deactivating else "USER.UPDATED",
                     entity_type="user", entity_id=u.id, before=before, after=_snapshot(db, u))
    return u


def reset_password(db: Session, actor: User, user_id: str, *,
                   institution_id: str | None = None) -> tuple[User, str]:
    u = _get(db, user_id, institution_id)
    temp = new_temporary_password()
    with uow(db):
        u.password_hash = hash_password(temp)
        sessions.revoke_user(db, u.id)
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="USER.PASSWORD_RESET",
                     entity_type="user", entity_id=u.id, after={"email": u.email})
    return u, temp


def list_users(db: Session, *, role: str | None = None, institution_id: str | None = None,
               active: bool | None = None, q: str | None = None, staff_of: str | None = None,
               limit: int = 50, offset: int = 0) -> tuple[list[User], int]:
    stmt = select(User)
    if staff_of is not None:
        stmt = stmt.where(User.institution_id == staff_of, User.role == Role.INSTITUTION_STAFF)
    if role:
        stmt = stmt.where(User.role == role)
    if institution_id:
        stmt = stmt.where(User.institution_id == institution_id)
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.email).limit(limit).offset(offset)).all()
    return list(rows), total
