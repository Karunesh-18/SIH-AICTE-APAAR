import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api import admin, auth, institutions, notifications
from app.db.session import SessionLocal
from app.services import clock_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Restore the demo clock offset saved before the last restart.
    try:
        with SessionLocal() as db:
            clock_admin.load(db)
    except OperationalError:  # tables do not exist yet on a first run, before migrations
        logging.getLogger(__name__).warning("clock offset not loaded: database not migrated")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Waymark APAAR Hub", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for r in (auth.router, institutions.router, notifications.router, admin.router):
        app.include_router(r, prefix="/api/v1")
    return app


app = create_app()
