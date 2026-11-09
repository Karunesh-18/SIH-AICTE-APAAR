from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import refuse, require_roles
from app.api.schemas import Strict
from app.db.session import get_db
from app.models.enums import AICTE_ROLES, INSTITUTION_ROLES
from app.models.user import User
from app.models.windows import SavedReport
from app.services import reports
from app.services.errors import Forbidden, Invalid, NotFound

router = APIRouter(prefix="/reports", tags=["reports"])
reader = require_roles(*AICTE_ROLES, *INSTITUTION_ROLES)  # verifiers get no reports


class SaveIn(Strict):
    name: str
    report_key: str
    filters: dict = Field(default_factory=dict)

    @field_validator("filters")
    @classmethod
    def _known(cls, v):
        bad = set(v) - set(reports.FILTERS) - {"group_by"}
        if bad:
            raise ValueError(f"unknown filters: {sorted(bad)}")
        return v


def _saved_out(s: SavedReport) -> dict:
    return {"id": s.id, "name": s.name, "report_key": s.report_key, "filters": s.filters,
            "created_at": s.created_at}


@router.get("")
def catalogue(_: User = Depends(reader)):
    return reports.catalogue()


@router.post("", status_code=201)
def save_report(body: SaveIn, user: User = Depends(reader), db: Session = Depends(get_db)):
    try:
        return _saved_out(reports.save(db, user, body.name, body.report_key, body.filters))
    except Invalid as e:
        raise HTTPException(422, str(e)) from None


@router.get("/saved")
def saved(user: User = Depends(reader), db: Session = Depends(get_db)):
    q = select(SavedReport).where(SavedReport.user_id == user.id).order_by(SavedReport.created_at)
    return [_saved_out(s) for s in db.scalars(q)]


@router.get("/{key}")
def run_report(key: str, format: Literal["json", "csv"] = "json", region: str | None = None,
               type: str | None = None, cycle_year: int | None = None,
               institution_id: str | None = None, group_by: str | None = None,
               user: User = Depends(reader), db: Session = Depends(get_db)):
    filters = {k: v for k, v in {"region": region, "type": type, "cycle_year": cycle_year,
                                 "institution_id": institution_id, "group_by": group_by}.items()
               if v is not None}
    try:
        result = reports.run(db, user, key, filters, format)
    except NotFound as e:
        raise HTTPException(404, str(e)) from None
    except Invalid as e:
        raise HTTPException(422, str(e)) from None
    except Forbidden as e:
        refuse(db, user, "institution", institution_id or "")
        raise HTTPException(403, str(e)) from None
    if format == "csv":
        return Response(reports.to_csv(result), media_type="text/csv", headers={
            "Content-Disposition": f'attachment; filename="{key}.csv"'})
    return result
