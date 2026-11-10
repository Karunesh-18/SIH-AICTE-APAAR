from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.masking import hint_out, mask_evidence
from app.api.records import mask_record, record_out
from app.api.schemas import Strict
from app.core import clock
from app.db.session import get_db
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES
from app.models.org import Institution
from app.models.student import FlagRecord, ValidationFlag
from app.models.user import User
from app.services import review

router = APIRouter(prefix="/flags", tags=["flags"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
reviewer = require_roles(*AICTE_ROLES)
replier = require_roles(*INSTITUTION_ROLES)
State = Literal["open", "under_review", "resolved", "dismissed", "ask_institution"]


class NoteIn(Strict):
    note: str
    lock_version: int | None = None

    @field_validator("note")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("A note is required")
        return v.strip()


def flag_out(f: ValidationFlag, institution_name: str, record_count: int) -> dict:
    return {
        "id": f.id, "rule_code": f.rule_code, "reason_key": f.reason_key, "reason": f.reason,
        "state": f.state, "institution_id": f.institution_id, "institution_name": institution_name,
        "assignee_id": f.assignee_id, "upload_id": f.upload_id, "lock_version": f.lock_version,
        "record_count": record_count, "created_at": f.created_at,
        "age_days": max((clock.now() - f.created_at).days, 0),
        "clear_hint": hint_out(f.rule_code, f.evidence),
    }


@router.get("")
def list_flags(state: State | None = None, rule: str | None = None,
               institution: str | None = None, region: str | None = None,
               age_days: int | None = Query(None, ge=0),
               limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
               user: User = Depends(reader), db: Session = Depends(get_db)):
    rows, total = review.list_flags(db, user, state=state, rule=rule, institution=institution,
                                    region=region, age_days=age_days, limit=limit, offset=offset)
    return {"items": [flag_out(f, i.name, n) for f, i, n in rows], "total": total}


@router.get("/{flag_id}")
def get_flag(flag_id: str, user: User = Depends(reader), db: Session = Depends(get_db)):
    d = _run(review.view, db, user, flag_id)
    f = d["flag"]
    rv = d["rule_version"]
    return flag_out(f, d["institution"].name, len(d["records"])) | {
        "evidence": mask_evidence(f.evidence, user),
        "rule_version": {"id": rv.id, "rule_code": rv.rule_code, "version_no": rv.version_no,
                         "params": rv.params, "message_en": rv.message_en,
                         "hard_stop": rv.hard_stop},
        "records": [mask_record(record_out(r, p), user, f.institution_id) for r, p in d["records"]],
        "events": [{"id": e.id, "from_state": e.from_state, "to_state": e.to_state,
                    "note": e.note, "at": e.at, "actor_id": e.actor_id,
                    "actor_name": u.full_name if u else "System",
                    "actor_role": u.role if u else None} for e, u in d["events"]],
    }


def _run(fn, *args):
    try:
        return fn(*args)
    except review.NotFound:
        raise HTTPException(404, "Flag not found") from None
    except review.Forbidden:
        raise HTTPException(403, "You do not have access to this flag") from None
    except review.Conflict as e:
        raise HTTPException(409, str(e)) from None


def _action(action: str, who):
    def endpoint(flag_id: str, body: NoteIn, user: User = Depends(who),
                 db: Session = Depends(get_db)):
        f = _run(review.act, db, user, flag_id, action, body.note, body.lock_version)
        n = db.scalar(select(func.count()).select_from(FlagRecord).where(FlagRecord.flag_id == f.id))
        return flag_out(f, db.get(Institution, f.institution_id).name, n)
    endpoint.__name__ = f"flag_{action}"
    router.add_api_route(f"/{{flag_id}}/{action}", endpoint, methods=["POST"])


for _a in ("review", "resolve", "dismiss", "ask", "link"):
    _action(_a, reviewer)
_action("reply", replier)
