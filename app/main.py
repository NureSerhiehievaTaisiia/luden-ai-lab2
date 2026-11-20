"""Application factory for educational Luden API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import init_db
from app.routes import router

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "app.db"


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Build the app. Database files are created only on lifespan startup, not on import."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        init_db(path)
        yield

    application = FastAPI(
        title="Luden Lab 02 API",
        description="Educational FastAPI+SQLite service implementing LR1 Luden rules for Lab 02.",
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.db_path = str(path)
    application.include_router(router)
    return application


# Uvicorn target: `python -m uvicorn app.main:app`
# Importing this module must NOT create data/app.db (init happens in lifespan).
app = create_app()
