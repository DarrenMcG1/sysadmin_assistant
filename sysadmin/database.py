"""Async SQLAlchemy engine and session management for PostgreSQL.

Provides:
- Async engine with search_path set to the sysadmin schema
- Session factory and context manager
- FastAPI dependency for request-scoped sessions
- Scheduler-safe session factory (NullPool, separate event loop)
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from sysadmin.config import get_config

logger = logging.getLogger(__name__)

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _configure_search_path(engine: Engine, schema: str) -> None:
    """Set search_path on every new connection for sync engines (Alembic)."""

    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema}, public")
        cursor.close()


async def create_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create the async engine and session factory.

    Uses server_settings to set search_path at the asyncpg protocol level,
    ensuring all queries target the sysadmin schema by default.
    """
    global _async_engine, _async_session_factory

    config = get_config()
    schema = config.database.schema_

    _async_engine = create_async_engine(
        config.database.url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "server_settings": {"search_path": f"{schema},public"}
        },
    )

    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return _async_engine, _async_session_factory


def get_engine() -> AsyncEngine:
    """Get the current async engine. Raises if not initialised."""
    if _async_engine is None:
        raise RuntimeError("Database engine not initialised. Call create_engine_and_session() first.")
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the current session factory. Raises if not initialised."""
    if _async_session_factory is None:
        raise RuntimeError("Session factory not initialised. Call create_engine_and_session() first.")
    return _async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Context manager for standalone async sessions (e.g. agents, services)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency — yields a request-scoped session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_scheduler_session() -> AsyncGenerator[AsyncSession]:
    """Session for scheduler jobs running in separate threads/event loops.

    Uses NullPool to avoid connection pool conflicts across event loops.
    Each call creates a fresh engine+connection — slightly slower, but safe.
    """
    config = get_config()
    schema = config.database.schema_

    engine = create_async_engine(
        config.database.url,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"search_path": f"{schema},public"}
        },
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await engine.dispose()


async def verify_connection() -> bool:
    """Test the database connection and check the sysadmin schema exists."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_schema()"))
            current_schema = result.scalar()
            logger.info("database_connected", extra={"schema": current_schema})

            # Ensure sysadmin schema exists
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sysadmin"))
            await conn.commit()
            return True
    except Exception as e:
        logger.error("database_connection_failed", extra={"error": str(e)})
        raise


async def dispose_engine() -> None:
    """Dispose the async engine, closing all pooled connections."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("database_engine_disposed")
