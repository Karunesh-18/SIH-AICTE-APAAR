"""Submission windows: CRUD and the reminder cycle. run_cycle is idempotent (the unique key on
window_alert_log) and reads time from the demo clock, so advancing the clock produces reminders.
It reminds and flags; it never penalises an institution."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.db.session import uow
from app.domain.ladder import plan
from app.models.org import Institution
from app.models.student import Upload
from app.models.user import User
from app.models.windows import SubmissionWindow, WindowAlertLog
from app.services import anomaly, audit, notify, validation
from app.services.errors import NotFound


def window_out(w: SubmissionWindow) -> dict:
    return {"id": w.id, "cycle_year": w.cycle_year, "institution_type": w.institution_type,
            "opens_at": w.opens_at, "closes_at": w.closes_at, "ladder": w.ladder}


def list_windows(db: Session) -> list[SubmissionWindow]:
    return list(db.scalars(select(SubmissionWindow).order_by(SubmissionWindow.closes_at.desc())))


def save(db: Session, actor: User, data: dict, window_id: str | None = None) -> SubmissionWindow:
    with uow(db):
        if window_id is None:
            w = SubmissionWindow(**data)
            db.add(w)
            action, before = "WINDOW.CREATED", None
        else:
            w = db.get(SubmissionWindow, window_id)
            if w is None:
                raise NotFound("Window not found")
            before = window_out(w)
            for k, v in data.items():
                setattr(w, k, v)
            action = "WINDOW.UPDATED"
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action=action,
                     entity_type="submission_window", entity_id=w.id,
                     before=before and {k: str(v) for k, v in before.items()},
                     after={k: str(v) for k, v in window_out(w).items()})
    return w


def _message(audience: str, inst: Institution, w: SubmissionWindow, step: dict) -> tuple[str, str]:
    day = w.closes_at.strftime("%d %B %Y")
    closed = step["offset_hours"] >= 0
    if audience == "institution":
        head = f"The {w.cycle_year} submission window closes on {day}."
        if closed:
            title = "Submission window closed" if step["offset_hours"] else "Submission window closes today"
            return title, f"{head} We have not received a submission from {inst.name}. Please upload your enrolment file."
        return "Submission window reminder", f"{head} We have not yet received a submission from {inst.name}."
    return ("Institution has not submitted",
            f"{inst.name} has not submitted for {w.cycle_year}. The window closed on {day}.")


def _recipients(db: Session, audience: str, inst: Institution) -> list[User]:
    if audience == "institution":
        return validation.institution_users(db, inst.id)
    if audience == "officer":
        return validation.region_officers(db, inst.region_id)
    return list(db.scalars(select(User).where(User.role == "AICTE_ADMIN", User.is_active)))


def run_cycle(db: Session, now: datetime | None = None, actor: User | None = None) -> dict:
    now = now or clock.now()
    out = {"sent": 0, "skipped": 0, "late": [], "flags": 0, "windows": 0}
    with uow(db):
        for w in list_windows(db):
            if now < w.opens_at:
                continue
            out["windows"] += 1
            q = select(Institution).where(Institution.status == "ACTIVE")
            if w.institution_type:
                q = q.where(Institution.type == w.institution_type)
            insts = list(db.scalars(q).unique())
            done = {i for (i,) in db.execute(select(Upload.institution_id).where(
                Upload.cycle_year == w.cycle_year).distinct())}
            for inst in insts:
                if inst.id in done:  # submitted: no reminders
                    continue
                if now > w.closes_at:
                    out["late"].append(inst.name)
                logged = set(db.scalars(select(WindowAlertLog.step).where(
                    WindowAlertLog.window_id == w.id, WindowAlertLog.institution_id == inst.id)))
                p = plan(w.ladder, w.closes_at, now, logged)
                for s in p.skip:
                    db.add(WindowAlertLog(window_id=w.id, institution_id=inst.id, step=s["step"],
                                          status="SKIPPED"))
                    out["skipped"] += 1
                for s in p.fire:
                    aud = s.get("audience", "institution")
                    db.add(WindowAlertLog(window_id=w.id, institution_id=inst.id, step=s["step"],
                                          status="SENT"))
                    subject, body = _message(aud, inst, w, s)
                    notify.enqueue(db, _recipients(db, aud, inst), subject=subject, body=body,
                                   related_type="submission_window", related_id=w.id)
                    out["sent"] += 1
            db.flush()
            out["flags"] += len(anomaly.run_in_tx(db, now, w.cycle_year, w, actor, insts))
        audit.append(db, actor_id=actor.id if actor else None,
                     actor_role=actor.role if actor else "SYSTEM", action="WINDOW.CYCLE_RUN",
                     entity_type="submission_window", entity_id="all",
                     after={k: (len(v) if k == "late" else v) for k, v in out.items()}
                     | {"now": now.isoformat()})
    return out
