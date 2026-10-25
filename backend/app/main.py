"""ScamDrill FastAPI application.

Serves the built frontend as static files plus the /api blueprint.
Single deployable: one Dockerfile builds frontend + runs this app.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .router import router, load_scenarios, _scenarios


def create_app() -> FastAPI:
    app = FastAPI(title="ScamDrill", version="0.1.0")

    # Load + validate scenarios on startup.
    _scenarios.update(load_scenarios())

    app.include_router(router)

    # Serve built frontend static files (Vite output dir: frontend/dist).
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("APP_ENV", "development") == "development",
    )