import json
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    _bearer,
    fail,
    get_current_user,
    institution_or_403,
    refuse,
    require_roles,
)
from app.api.masking import _mask_name, hint_out, mask_evidence
from app.api.schemas import Strict
from app.api.uploads import upload_out
from app.db.session import get_db, uow
from app.domain.apaar import mask
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.org import Institution, Programme
from app.models.student import FlagRecord, StudentRecord, ValidationFlag
from app.models.user import User
from app.services import apikeys, audit, certificates, ingest, records
from app.services import errors as E
from app.services.access import can_access_institution

router = APIRouter(tags=["records"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
Status = Literal["submitted", "valid", "flagged", "pending_apaar", "withdrawn"]


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
    found = {v.id: v for v in db.scalars(chain)}
    for _step, link in (("back", "continues_record_id"), ("forward", "superseded_by")):
        cur = rec  # a correction can change the APAAR ID, so follow the links as well
        while (nxt := getattr(cur, link)) and nxt not in found and (cur := db.get(StudentRecord, nxt)):
            found[cur.id] = cur
    versions = sorted(found.values(), key=lambda v: (v.version, v.row_number or 0))
    flags = db.scalars(select(ValidationFlag).join(
        FlagRecord, FlagRecord.flag_id == ValidationFlag.id).where(
        FlagRecord.record_id == rec.id)).all()
    out = mask_record(record_out(rec, prog), user, prog.institution_id)
    out["versions"] = [{"id": v.id, "version": v.version, "is_current": v.is_current,
                        "upload_id": v.upload_id, "status": v.status,
                        "superseded_at": v.superseded_at} for v in versions]
    out["flags"] = [{"id": f.id, "rule_code": f.rule_code, "state": f.state, "reason": f.reason,
                     "evidence": mask_evidence(f.evidence, user),
                     "clear_hint": hint_out(f.rule_code, f.evidence)} for f in flags]
    return out


@router.post("/records/{record_id}/certificate")
def certificate(record_id: str, user: User = Depends(reader), db: Session = Depends(get_db)):
    try:
        with uow(db):
            return certificates.issue(db, user, record_id)
    except (E.Forbidden, E.NotFound, E.Conflict) as e:
        raise fail(db, user, e, "student_record", record_id) from None


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


# ---- corrections and withdrawal ------------------------------------------------------------------

editor = require_roles(Role.AICTE_ADMIN, *INSTITUTION_ROLES)


class CorrectionIn(Strict):
    """Only these fields can change; the programme and cycle are fixed by the upload."""
    apaar_id: str | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    dob: date | None = None
    year_of_study: int | None = Field(None, ge=1)
    admission_date: date | None = None
    admission_category: str | None = Field(None, min_length=1, max_length=32)
    nri: bool | None = None
    oci: bool | None = None
    fn: bool | None = None


class WithdrawIn(Strict):
    reason: str

    @field_validator("reason")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("A reason is required")
        return v.strip()


def _call(fn, *args):
    try:
        return fn(*args)
    except E.NotFound:
        raise HTTPException(404, "Record not found") from None
    except E.Forbidden:
        raise HTTPException(403, "You do not have access to this record") from None
    except E.Conflict as e:
        raise HTTPException(409, str(e)) from None
    except E.Invalid as e:
        raise HTTPException(422, str(e)) from None


def _flag_brief(f: ValidationFlag) -> dict:
    return {"id": f.id, "rule_code": f.rule_code, "reason": f.reason, "state": f.state}


@router.patch("/records/{record_id}")
def correct_record(record_id: str, body: CorrectionIn, user: User = Depends(editor),
                   db: Session = Depends(get_db)):
    res = _call(records.correct, db, user, record_id, body.model_dump(exclude_none=True))
    owner = res["programme"].institution_id
    return {"record": mask_record(record_out(res["new"], res["programme"]), user, owner),
            "previous": mask_record(record_out(res["old"], res["programme"]), user, owner),
            "closed_flags": [_flag_brief(f) for f in res["closed"]],
            "raised_flags": [_flag_brief(f) for f in res["raised"]]}


@router.post("/records/{record_id}/withdraw")
def withdraw_record(record_id: str, body: WithdrawIn, user: User = Depends(editor),
                    db: Session = Depends(get_db)):
    rec = _call(records.withdraw, db, user, record_id, body.reason)
    prog = db.get(Programme, rec.programme_id)
    return mask_record(record_out(rec, prog) | {"withdrawn_reason": rec.withdrawn_reason},
                       user, prog.institution_id)
