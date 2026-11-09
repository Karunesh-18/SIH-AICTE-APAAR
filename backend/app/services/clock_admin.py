"""Demo clock: move 'now' forward to show reminders and late lists. Offset survives restarts."""
from sqlalchemy.orm import Session

from app.core import clock
from app.db.session import uow
from app.models.system import SystemConfig
from app.models.user import User
from app.services import audit

KEY = "clock_offset_seconds"


def load(db: Session) -> None:
    row = db.get(SystemConfig, KEY)
    clock.set_offset(row.value["seconds"] if row else 0)


def set_clock(db: Session, actor: User, advance_days: float | None, reset: bool) -> float:
    before = clock.get_offset_seconds()
    after = 0.0 if reset else before + (advance_days or 0) * 86400
    with uow(db):
        row = db.get(SystemConfig, KEY)
        if row is None:
            db.add(SystemConfig(key=KEY, value={"seconds": after}))
        else:
            row.value = {"seconds": after}
        clock.set_offset(after)
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action="CLOCK.SET",
                     entity_type="clock", entity_id=KEY,
                     before={"seconds": before}, after={"seconds": after})
    return after
