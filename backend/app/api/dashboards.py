from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import institution_or_403, require_roles
from app.core import clock
from app.db.session import get_db
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES, Role
from app.models.org import Programme, Region
from app.models.student import StudentRecord, Upload, ValidationFlag
from app.models.user import User, UserRegion
from app.services import metrics

router = APIRouter(tags=["dashboards"])
aicte_only = require_roles(*AICTE_ROLES)
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)
InstType = Literal["ENGINEERING", "MANAGEMENT", "PHARMACY", "OTHER"]


def _cycle(db, cycle_year):
    return cycle_year or metrics.default_cycle(db)


@router.get("/regions")
def regions(user: User = Depends(reader), db: Session = Depends(get_db)):
    q = select(Region).order_by(Region.name)
    if user.role == Role.AICTE_OFFICER:
        q = q.join(UserRegion, UserRegion.region_id == Region.id).where(
            UserRegion.user_id == user.id)
    elif user.role in INSTITUTION_ROLES:
        return []
    return [{"id": r.id, "code": r.code, "name": r.name} for r in db.scalars(q)]


@router.get("/dashboards/aicte")
def aicte_dashboard(region: str | None = None, type: InstType | None = None,
                    state: Literal["Clear", "Alert", "Excess"] | None = None,
                    cycle_year: int | None = None, user: User = Depends(aicte_only),
                    db: Session = Depends(get_db)):
    cycle = _cycle(db, cycle_year)
    # tiles describe everything in scope; the filters only narrow the table
    scope = metrics.institution_table(db, user, cycle)
    share = metrics.pending_share(db, [r["id"] for r in scope], cycle)
    table = metrics.institution_table(db, user, cycle, region=region, type_=type, state=state)
    return {"cycle_year": cycle, "tiles": metrics.aicte_tiles(scope, share), "institutions": table}


@router.get("/dashboards/institution")
def institution_dashboard(institution_id: str | None = None, user: User = Depends(reader),
                          db: Session = Depends(get_db)):
    iid = institution_id or (user.institution_id if user.role in INSTITUTION_ROLES else None)
    if iid is None:
        raise HTTPException(422, "institution_id is required")
    inst = institution_or_403(db, user, iid)
    cycle = metrics.default_cycle(db)
    mine = (StudentRecord.programme_id.in_(
        select(Programme.id).where(Programme.institution_id == inst.id)),
        *metrics.current_filters(cycle))
    n = lambda *c: db.scalar(select(func.count()).select_from(StudentRecord).where(*mine, *c))
    open_q = select(ValidationFlag).where(ValidationFlag.institution_id == inst.id).order_by(
        ValidationFlag.created_at.desc())
    flag = lambda f: {"id": f.id, "rule": f.rule_code, "reason": f.reason, "state": f.state}
    flags = db.scalars(open_q.where(ValidationFlag.state.in_(("open", "under_review")))).all()
    asks = db.scalars(open_q.where(ValidationFlag.state == "ask_institution")).all()
    pending = db.execute(select(StudentRecord.id, StudentRecord.row_number).where(
        *mine, StudentRecord.status == "pending_apaar").order_by(StudentRecord.row_number)).all()
    submitted = bool(db.scalar(select(func.count()).select_from(Upload).where(
        Upload.institution_id == inst.id, Upload.cycle_year == cycle)))
    w, now, window = metrics.window_for(db, inst, cycle), clock.now(), None
    if w:
        window = {"cycle_year": w.cycle_year, "opens_at": w.opens_at, "closes_at": w.closes_at,
                  "state": "not_open" if now < w.opens_at else "open" if now <= w.closes_at
                  else "closed", "submitted": submitted,
                  "hours_to_close": round((w.closes_at - now).total_seconds() / 3600, 1)}
    return {"institution": {"id": inst.id, "name": inst.name}, "cycle_year": cycle,
            "window": window, "submitted": submitted,
            "records": {"accepted": n(), "flagged": n(StudentRecord.status == "flagged"),
                        "pending_apaar": n(StudentRecord.status == "pending_apaar")},
            "todo": {"open_flags": [flag(f) for f in flags], "asks": [flag(f) for f in asks],
                     "pending_apaar": [{"record_id": r, "row_number": rn} for r, rn in pending]}}


@router.get("/dashboards/intake-use")
def intake_use(region: str | None = None, type: InstType | None = None,
               cycle_year: int | None = None, user: User = Depends(reader),
               db: Session = Depends(get_db)):
    cycle = _cycle(db, cycle_year)
    ids = [i.id for i in metrics.scoped_institutions(db, user, region=region, type_=type)]
    return {"cycle_year": cycle, "rows": metrics.programme_rows(db, ids, cycle)}


@router.get("/dashboards/flags-trend")
def flags_trend(region: str | None = None, type: InstType | None = None,
                user: User = Depends(reader), db: Session = Depends(get_db)):
    ids = [i.id for i in metrics.scoped_institutions(db, user, region=region, type_=type)]
    return {"rows": metrics.flags_by_rule_month(db, ids)}
