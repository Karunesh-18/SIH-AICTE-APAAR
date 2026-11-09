from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db, uow
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.org import Institution
from app.models.user import User
from app.services import audit
from app.services.access import can_access_institution, officer_region_ids

router = APIRouter(prefix="/institutions", tags=["institutions"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    aicte_id: str
    name: str
    type: str
    status: str
    contact_email: str | None
    region: RegionOut


@router.get("", response_model=list[InstitutionOut])
def list_institutions(user: User = Depends(reader), db: Session = Depends(get_db)):
    q = select(Institution).order_by(Institution.name)
    if user.role == Role.AICTE_OFFICER:
        q = q.where(Institution.region_id.in_(officer_region_ids(db, user)))
    elif user.role in INSTITUTION_ROLES:
        q = q.where(Institution.id == user.institution_id)
    return db.scalars(q).unique().all()


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(institution_id: str, user: User = Depends(reader),
                    db: Session = Depends(get_db)):
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(404, "Institution not found")
    if not can_access_institution(db, user, inst):
        with uow(db):  # refusals are logged
            audit.append(db, actor_id=user.id, actor_role=user.role, action="ACCESS.REFUSED",
                         entity_type="institution", entity_id=inst.id)
        raise HTTPException(403, "You do not have access to this institution")
    return inst
