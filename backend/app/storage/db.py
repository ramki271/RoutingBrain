from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_db_engine(database_url: str) -> AsyncEngine:
    """Create shared async SQLAlchemy engine for app storage modules."""
    return create_async_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )
