"""Object-level scope. Role checks alone are not enough: a user must also own the object."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import INSTITUTION_ROLES, Role
from app.models.org import Institution
from app.models.user import User, UserRegion


def officer_region_ids(db: Session, user: User) -> set[str]:
    return set(db.scalars(select(UserRegion.region_id).where(UserRegion.user_id == user.id)))


def can_access_institution(db: Session, user: User, inst: Institution) -> bool:
    if user.role == Role.AICTE_ADMIN:
        return True
    if user.role == Role.AICTE_OFFICER:
        return inst.region_id in officer_region_ids(db, user)
    if user.role in INSTITUTION_ROLES:
        return user.institution_id == inst.id
    return False  # verifiers never read institutions
