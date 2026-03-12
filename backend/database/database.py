"""
database.py — SQLAlchemy engine, session factory, and declarative base.

Reads DATABASE_URL from environment. If the variable is not set or the
database is unreachable, the module loads without error so that the
existing CSV-based backtest workflow is completely unaffected.
"""
from __future__ import annotations

import os
import contextlib
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.settings import DATABASE_URL

# ── Connection ────────────────────────────────────────────────────────────────

# If no URL is configured, we create a lightweight SQLite fallback so that
# all imports resolve without error (SQLite needs no separate server).
_effective_url = DATABASE_URL or "sqlite:///./algotradex_local.db"
_is_postgres    = _effective_url.startswith("postgresql")

# Since this backend relies on synchronous SQLAlchemy execution, if the user
# provides an asyncpg URL (e.g. postgresql+asyncpg), we will route it through psycopg2.
if _is_postgres and "+asyncpg" in _effective_url:
    _effective_url = _effective_url.replace("+asyncpg", "+psycopg2")
elif _is_postgres and "://" in _effective_url and "+psycopg2" not in _effective_url:
    _effective_url = _effective_url.replace("postgresql://", "postgresql+psycopg2://")

_connect_args = {"check_same_thread": False} if not _is_postgres else {}

engine = create_engine(
    _effective_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base class ────────────────────────────────────────────────────────────────
Base = declarative_base()


# ── Dependency for FastAPI routes ─────────────────────────────────────────────
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auto-create tables (idempotent) ───────────────────────────────────────────
def init_db() -> None:
    """Create all tables that don't yet exist. Safe to call on every startup."""
    import backend.database.models  # noqa: F401 — registers models with Base metadata
    with contextlib.suppress(Exception):
        Base.metadata.create_all(bind=engine)
