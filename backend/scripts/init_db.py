"""Create tables on Neon PostgreSQL. Does not drop or overwrite existing tables.

Usage (from the backend directory):

    set DATABASE_URL_UNPOOLED=postgresql://...
    python scripts/init_db.py

Alembic is not part of this project. SQLAlchemy metadata creates missing tables
only. It will not alter columns that already exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.database import normalize_database_url
from app.models import Dataset, ImportBatch, TransactionLine, User  # noqa: F401
from app.database import Base


def _postgres_url() -> str:
    raw = os.getenv("DATABASE_URL_UNPOOLED", "").strip() or os.getenv("DATABASE_URL", "").strip()
    if not raw:
        print(
            "DATABASE_URL_UNPOOLED or DATABASE_URL is not set. "
            "Refusing to create a SQLite database.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    url = normalize_database_url(raw)
    if not url.startswith("postgresql"):
        print("Schema init requires a PostgreSQL URL. SQLite was not used.", file=sys.stderr)
        raise SystemExit(1)
    return url


def main() -> None:
    url = _postgres_url()
    scheme = url.split("://", 1)[0]
    print(f"Connecting with driver {scheme}.")
    engine = create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
    except Exception:
        print("Schema initialization failed. The database URL and error details were not printed.", file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        engine.dispose()
    print("Schema initialized. Existing tables were left in place.")


if __name__ == "__main__":
    main()
