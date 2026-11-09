import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import _bearer, get_current_user, institution_or_403, refuse, require_roles
from app.api.schemas import Strict
from app.api.uploads import upload_out
from app.db.session import get_db, uow
from app.domain.apaar import mask
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES
from app.models.org import Institution, Programme
from app.models.student import FlagRecord, StudentRecord, ValidationFlag
from app.models.user import User
from app.services import apikeys, audit, ingest
from app.services.access import can_access_institution

router = APIRouter(tags=["records"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
Status = Literal["submitted", "valid", "flagged", "pending_apaar", "withdrawn"]


def _mask_name(name: str) -> str:
    return " ".join(w[0] + "*" * (len(w) - 1) for w in name.split())


def mask_record(rec: dict, viewer, owner_institution_id: str) -> dict:
    """Serializer-level masking. Unmasked only for AICTE roles and the record's own institution."""
    if viewer.role in AICTE_ROLES or viewer.institution_id == owner_institution_id:
        return rec
    return rec | {"apaar_id": mask(rec["apaar_id"]), "name": _mask_name(rec["name"]),
                  "dob": f"{str(rec['dob'])[:4]}-**-**"}


def record_out(r: StudentRecord, programme: Programme) -> dict:
    return {
        "id": r.id, "apaar_id": r.apaar_id, "name": r.name, "dob": r.dob.isoformat(),
        "programme": programme.name, "cycle_year": r.cycle_year,
        "year_of_study": r.year_of_study, "admission_date": r.admission_date.isoformat(),
        "admission_category": r.admission_category, "nri": r.nri, "oci": r.oci, "fn": r.fn,
        "status": r.status, "version": r.version, "is_current": r.is_current,
        "upload_id": r.upload_id, "row_number": r.row_number,
    }


@router.get("/institutions/{institution_id}/records")
def list_records(institution_id: str, status: Status | None = None,
                 limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
                 user: User = Depends(reader), db: Session = Depends(get_db)):
    institution_or_403(db, user, institution_id)
    q = (select(StudentRecord, Programme).join(Programme)
         .where(Programme.institution_id == institution_id, StudentRecord.is_current))
    if status:
        q = q.where(StudentRecord.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(StudentRecord.upload_id, StudentRecord.row_number,
                                 StudentRecord.id).limit(limit).offset(offset)).all()
    return {"items": [mask_record(record_out(r, p), user, institution_id) for r, p in rows],
            "total": total}


@router.get("/records/{record_id}")
def get_record(record_id: str, user: User = Depends(reader), db: Session = Depends(get_db)):
    rec = db.get(StudentRecord, record_id)
    if rec is None:
        raise HTTPException(404, "Record not found")
    prog = db.get(Programme, rec.programme_id)
    if not can_access_institution(db, user, db.get(Institution, prog.institution_id)):
        refuse(db, user, "student_record", rec.id)
        raise HTTPException(403, "You do not have access to this record")
    with uow(db):  # a single-record view is audited
        audit.append(db, actor_id=user.id, actor_role=user.role, action="RECORD.VIEWED",
                     entity_type="student_record", entity_id=rec.id)
    chain = (select(StudentRecord).where(StudentRecord.programme_id == rec.programme_id,
                                         StudentRecord.cycle_year == rec.cycle_year,
                                         StudentRecord.apaar_id == rec.apaar_id)
             if rec.apaar_id else select(StudentRecord).where(StudentRecord.id == rec.id))
    versions = db.scalars(chain.order_by(StudentRecord.version, StudentRecord.row_number)).all()
    flags = db.scalars(select(ValidationFlag).join(
        FlagRecord, FlagRecord.flag_id == ValidationFlag.id).where(
        FlagRecord.record_id == rec.id)).all()
    out = mask_record(record_out(rec, prog), user, prog.institution_id)
    out["versions"] = [{"id": v.id, "version": v.version, "is_current": v.is_current,
                        "upload_id": v.upload_id, "status": v.status,
                        "superseded_at": v.superseded_at} for v in versions]
    out["flags"] = [{"id": f.id, "rule_code": f.rule_code, "state": f.state, "reason": f.reason,
                     "evidence": f.evidence} for f in flags]
    return out


# ---- JSON batch push: signed-in user or API key ------------------------------------------------

class StudentsIn(Strict):
    cycle_year: int
    students: list[dict[str, Any]]


@router.post("/institutions/{institution_id}/students")
def push_students(institution_id: str, body: StudentsIn,
                  x_api_key: str | None = Header(None),
                  creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                  db: Session = Depends(get_db)):
    user = key = None
    if x_api_key:
        key = apikeys.find(db, x_api_key)
        if key is None:
            raise HTTPException(401, "Invalid API key")
        if key.revoked_at is not None:
            apikeys.record_use(db, key, "APIKEY.REFUSED", reason="revoked")
            raise HTTPException(401, "Invalid API key")
        if key.institution_id != institution_id or key.scope != apikeys.SCOPE:
            apikeys.record_use(db, key, "APIKEY.REFUSED", reason="out of scope",
                               requested_institution=institution_id)
            raise HTTPException(403, "This key cannot submit for that institution")
        apikeys.record_use(db, key)
    else:
        user = get_current_user(creds, db)
        if user.role not in {r.value for r in (*AICTE_ROLES, *INSTITUTION_ROLES)}:
            raise HTTPException(403, "Not allowed for your role")
        institution_or_403(db, user, institution_id)
    data = json.dumps({"students": body.students}).encode()
    up = ingest.ingest(db, actor=user, institution_id=institution_id, cycle_year=body.cycle_year,
                       data=data, source="API", fmt="api", api_key_id=key.id if key else None)
    return upload_out(db, up)
