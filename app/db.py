"""
SQLite + SQLAlchemy (async) setup.
Tables are created automatically at startup via FastAPI lifespan (see main.py).
Deleting data/analyzer.db resets all history.
"""
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create the parent folder for a sqlite file URL if it doesn't exist."""
    match = re.match(r"sqlite\+aiosqlite:///(.+)", database_url)
    if match:
        db_path = Path(match.group(1))
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.DATABASE_URL)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if they don't exist. Called from the FastAPI lifespan."""
    # Import models so they are registered on Base.metadata
    from app import models_db  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
