"""Rule health: gather flag facts and hand them to the pure summary. Read only, not audited."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.domain import rule_health
from app.domain.flags import TERMINAL
from app.models.rules import Rule
from app.models.student import FlagEvent, FlagRecord, StudentRecord, ValidationFlag


def health(db: Session, cycle: int | None = None, institution_id: str | None = None) -> list[dict]:
    q = select(ValidationFlag)
    if institution_id:
        q = q.where(ValidationFlag.institution_id == institution_id)
    if cycle:  # a flag belongs to the cycle of the records it points at
        q = q.where(ValidationFlag.id.in_(
            select(FlagRecord.flag_id).join(StudentRecord, StudentRecord.id == FlagRecord.record_id)
            .where(StudentRecord.cycle_year == cycle)))
    flags = db.scalars(q).all()
    closed_at: dict[str, object] = {}
    for fid, at in db.execute(select(FlagEvent.flag_id, FlagEvent.at).where(
            FlagEvent.to_state.in_(TERMINAL)).order_by(FlagEvent.at)):
        closed_at[fid] = at  # the latest move into a terminal state
    rows = [(f.rule_code, f.state, f.created_at,
             closed_at.get(f.id) if f.state in TERMINAL else None) for f in flags]
    codes = list(db.scalars(select(Rule.code).order_by(Rule.code)))
    return rule_health.summarise(codes, rows, clock.now())
