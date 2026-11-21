import os

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

_MISSING_DATABASE_DETAIL = (
    "DATABASE_URL is not configured. Set the Neon pooled Postgres connection string "
    "on the backend Vercel project. Production does not fall back to SQLite."
)


def normalize_database_url(url: str) -> str:
    """Accept postgres:// and postgresql:// and use the psycopg 3 driver."""
    cleaned = url.strip()
    if cleaned.startswith("postgres://"):
        return "postgresql+psycopg://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://"):
        return "postgresql+psycopg://" + cleaned[len("postgresql://") :]
    return cleaned


def production_database_url() -> str | None:
    """Return a Postgres URL in production, or None when it is missing or SQLite."""
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return None
    url = normalize_database_url(raw)
    if url.startswith("sqlite"):
        return None
    if not url.startswith("postgresql"):
        return None
    return url


def _build_engine(url: str):
    if url.startswith("postgresql"):
        # NullPool: one connection per request, which fits Neon pooled serverless use.
        return create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


if settings.is_production():
    _runtime_url = production_database_url()
else:
    _runtime_url = normalize_database_url(os.getenv("DATABASE_URL", "").strip() or settings.database_url)

if _runtime_url:
    engine = _build_engine(_runtime_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


class Base(DeclarativeBase):
    pass


def database_status() -> tuple[bool, str]:
    """Check connectivity. Never include the URL or exception text (it can contain a password)."""
    if engine is None:
        return False, "not_configured"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception:
        return False, "unavailable"


def get_db():
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_MISSING_DATABASE_DETAIL,
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
