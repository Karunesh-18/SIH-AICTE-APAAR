import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import institution_or_403, refuse, require_roles
from app.db.session import get_db, get_session_factory
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.org import Institution
from app.models.student import FlagRecord, StudentRecord, Upload, ValidationFlag
from app.models.user import User
from app.services import ingest
from app.services.access import officer_region_ids

router = APIRouter(tags=["uploads"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
MAX_BYTES = 10 * 1024 * 1024
log = logging.getLogger(__name__)


def upload_out(db: Session, up: Upload) -> dict:
    by_rule = dict(db.execute(select(ValidationFlag.rule_code, func.count()).where(
        ValidationFlag.upload_id == up.id).group_by(ValidationFlag.rule_code)).all())
    return {
        "id": up.id, "institution_id": up.institution_id, "cycle_year": up.cycle_year,
        "source": up.source, "format": up.format, "status": up.status,
        "row_count": up.row_count if up.status in ("DONE", "REJECTED") else None,
        "accepted_count": up.accepted_count, "flagged_count": up.flagged_count,
        "error": up.error, "created_at": up.created_at,
        "flags": {"total": sum(by_rule.values()), "by_rule": by_rule},
    }


def run_in_background(factory, upload_id: str, data: bytes) -> None:
    # ponytail: in-process, move to a queue at scale
    db = factory()
    try:
        ingest.process(db, upload_id, data)
    except Exception:  # noqa: BLE001  already logged and marked; a background task must not raise
        log.warning("background processing of upload %s failed", upload_id)
    finally:
        db.close()


@router.post("/uploads", status_code=202)
def post_upload(background: BackgroundTasks, file: UploadFile = File(...),
                cycle_year: int = Form(..., ge=2000, le=2100),
                institution_id: str | None = Form(None), user: User = Depends(reader),
                db: Session = Depends(get_db), factory=Depends(get_session_factory)):
    if user.role in {r.value for r in INSTITUTION_ROLES}:
        if institution_id and institution_id != user.institution_id:
            refuse(db, user, "institution", institution_id)
            raise HTTPException(403, "You can only upload for your own institution")
        inst_id = user.institution_id
    else:
        if not institution_id:
            raise HTTPException(422, "institution_id is required for AICTE users")
        inst_id = institution_or_403(db, user, institution_id).id
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 10 MB")
    up = ingest.receive(db, actor=user, institution_id=inst_id, cycle_year=cycle_year, data=data)
    background.add_task(run_in_background, factory, up.id, data)
    return {"id": up.id, "status": up.status, "row_count": None}


@router.get("/uploads")
def list_uploads(limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
                 user: User = Depends(reader), db: Session = Depends(get_db)):
    q = select(Upload)
    if user.role == Role.AICTE_OFFICER:
        q = q.join(Institution, Upload.institution_id == Institution.id).where(
            Institution.region_id.in_(officer_region_ids(db, user)))
    elif user.role in INSTITUTION_ROLES:
        q = q.where(Upload.institution_id == user.institution_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Upload.created_at.desc(), Upload.id).limit(limit).offset(offset))
    return {"items": [upload_out(db, u) for u in rows], "total": total}


@router.get("/uploads/{upload_id}")
def get_upload(upload_id: str, user: User = Depends(reader), db: Session = Depends(get_db)):
    up = db.get(Upload, upload_id)
    if up is None:
        raise HTTPException(404, "Upload not found")
    institution_or_403(db, user, up.institution_id)
    flags = db.scalars(select(ValidationFlag).where(ValidationFlag.upload_id == up.id)
                       .order_by(ValidationFlag.rule_code, ValidationFlag.id)).all()
    items = []
    for f in flags:
        rows = db.scalars(select(StudentRecord.row_number).join(
            FlagRecord, FlagRecord.record_id == StudentRecord.id).where(
            FlagRecord.flag_id == f.id).order_by(StudentRecord.row_number)).all()
        items.append({"id": f.id, "rule_code": f.rule_code, "reason_key": f.reason_key,
                      "reason": f.reason, "evidence": f.evidence, "rows": rows})
    return upload_out(db, up) | {"flag_items": items}


@router.get("/templates/{fmt}")
def template(fmt: str, _: User = Depends(reader)):
    if fmt == "csv":
        body, ctype = ingest.template_csv(), "text/csv; charset=utf-8"
    elif fmt == "xlsx":
        body = ingest.template_xlsx()
        ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(404, "Template formats are csv and xlsx")
    return Response(body, media_type=ctype,
                    headers={"Content-Disposition": f'attachment; filename="students-template.{fmt}"'})
