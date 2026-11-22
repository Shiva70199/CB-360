import os
import sys
import threading
import logging

from fastapi import HTTPException, Request, status
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

_MISSING_DATABASE_DETAIL = (
    "DATABASE_URL is not configured. Set the Neon pooled Postgres connection string "
    "on the backend Vercel project. Production does not fall back to SQLite."
)
logger = logging.getLogger("cb360.database")


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
        # Neon’s pooled URL is PgBouncer in transaction mode. psycopg 3 prepares
        # statements on the client connection, and that pooler may bind the next
        # statement to a different server connection. Keep one short-lived
        # connection per request and do not prepare.
        return create_engine(
            url,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
        )
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
            if str(engine.url).startswith("postgresql"):
                connection.execute(text("SELECT user_id FROM transaction_lines LIMIT 0"))
        return True, "ok"
    except Exception:
        return False, "unavailable"


_schema_ready = False
_schema_lock = threading.Lock()


def _schema_binds():
    """Prefer the direct Neon URL for DDL, then the pooled runtime engine."""
    binds = []
    raw = os.getenv("DATABASE_URL_UNPOOLED", "").strip()
    if raw:
        url = normalize_database_url(raw)
        if url.startswith("postgresql"):
            binds.append(_build_engine(url))
    if engine is not None:
        binds.append(engine)
    return binds


def ensure_schema() -> None:
    """Create missing tables once per process. Does not drop or alter existing data."""
    global _schema_ready
    if _schema_ready or engine is None:
        return
    if not str(engine.url).startswith("postgresql"):
        _schema_ready = True
        return
    with _schema_lock:
        if _schema_ready:
            return
        # Import after startup so model tables are registered on Base.metadata.
        from app import models  # noqa: F401

        for bind in _schema_binds():
            try:
                Base.metadata.create_all(bind=bind)
                _schema_ready = True
                return
            except Exception as exc:
                print(f"schema_init_failed {type(exc).__name__}", file=sys.stderr)
            finally:
                if bind is not engine:
                    bind.dispose()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database schema is not ready. Run python scripts/init_db.py with DATABASE_URL_UNPOOLED.",
        ) from None


def _quiet_session_call(db, method: str) -> None:
    try:
        getattr(db, method)()
    except Exception as exc:
        print(f"db_{method}_failed {type(exc).__name__}", file=sys.stderr)


def get_db(request: Request):
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_MISSING_DATABASE_DETAIL,
        )
    ensure_schema()
    db = SessionLocal()
    try:
        yield db
    except HTTPException:
        _quiet_session_call(db, "rollback")
        raise
    except SQLAlchemyError as exc:
        _quiet_session_call(db, "rollback")
        logger.error(
            "api_failure request_id=%s endpoint=%s failure_stage=db_transaction exception_type=%s http_status=503",
            getattr(request.state, "request_id", "unknown"),
            request.url.path,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database could not complete that request.",
        ) from None
    except Exception:
        _quiet_session_call(db, "rollback")
        raise
    finally:
        _quiet_session_call(db, "close")
