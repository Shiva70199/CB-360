"""Import the local California Burrito workbook into Neon.

Run once from the backend directory, using the direct Neon connection:

    set DATABASE_URL_UNPOOLED=postgresql://...
    python scripts/import_restaurant.py

The workbook is read from RESTAURANT_SOURCE_PATH or
data/source/restaurant_transactions.xlsx. It is not uploaded to GitHub.

The import is safe to repeat: a file that already imported successfully is reused
instead of inserting the same line items again. Line revenue is price x quantity.
Orders are grouped by bill number, outlet, and calendar date.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, normalize_database_url
from app.etl import import_restaurant_file
from app.models import Dataset, ImportBatch, TransactionLine, User  # noqa: F401


def _postgres_url() -> str:
    raw = os.getenv("DATABASE_URL_UNPOOLED", "").strip() or os.getenv("DATABASE_URL", "").strip()
    if not raw:
        print(
            "DATABASE_URL_UNPOOLED is not set. Provide the Neon direct connection string.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    url = normalize_database_url(raw)
    if not url.startswith("postgresql"):
        print("Import requires PostgreSQL. Refusing to write to SQLite.", file=sys.stderr)
        raise SystemExit(1)
    return url


def main() -> None:
    source = settings.resolve_restaurant_source_path()
    if not source.exists():
        print(f"Workbook not found: {source}")
        print("Place restaurant_transactions.xlsx at that path. It is gitignored and was not imported.")
        raise SystemExit(2)

    url = _postgres_url()
    print(f"Importing {source.name} using driver {url.split('://', 1)[0]}.")
    engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    try:
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            batch = import_restaurant_file(db, file_path=source)
            counts = db.execute(
                text(
                    "SELECT COUNT(*) AS lines, COUNT(DISTINCT order_key) AS orders "
                    "FROM transaction_lines"
                )
            ).one()
        finally:
            db.close()
    except SystemExit:
        raise
    except Exception:
        print("Import failed. Connection details were not printed.", file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        engine.dispose()

    print("Import validation")
    print(f"  status: {batch.status}")
    print(f"  file_hash: {batch.file_hash}")
    print(f"  total_rows: {batch.total_rows}")
    print(f"  valid_rows: {batch.valid_rows}")
    print(f"  rejected_rows: {batch.rejected_rows}")
    print(f"  notes: {batch.notes or ''}")
    print(f"  stored_line_items: {counts.lines}")
    print(f"  distinct_orders: {counts.orders}")
    if batch.notes == "reused_existing_import":
        print("  repeat: existing successful import was reused; no duplicate lines were inserted.")
    if batch.status != "success" and batch.notes != "reused_existing_import":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
