"""Runs the window cycle on an interval. Off in demo mode (the demo clock and the admin button
drive it) unless SCHEDULER=1; always on outside demo mode. Tests never start it."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import notify, windows

log = logging.getLogger(__name__)


def should_run(*, demo_mode: bool, scheduler_flag: bool) -> bool:
    return scheduler_flag or not demo_mode


def _tick() -> None:
    try:
        with SessionLocal() as db:
            windows.run_cycle(db)  # dispatches the outbox itself
            notify.dispatch_now(db)  # and retries anything left over from earlier failures
    except Exception:
        log.exception("window cycle failed")


def start() -> BackgroundScheduler:
    sched = BackgroundScheduler()
    sched.add_job(_tick, "interval", minutes=settings.scheduler_minutes, id="window-cycle")
    sched.start()
    return sched
