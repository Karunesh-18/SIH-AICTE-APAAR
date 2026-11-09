from fastapi import FastAPI

from app.api import auth


def create_app() -> FastAPI:
    app = FastAPI(title="Waymark APAAR Hub", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
