"""Add TransactionLine.user_id safely and backfill only reliable ownership.

Usage:
  set DATABASE_URL_UNPOOLED=postgresql://...
  python scripts/migrate_add_transaction_user.py

This migration only:
- adds a nullable users.id foreign key column and index
- backfills transaction_lines.user_id from import_batches.user_id where that batch
  has exactly one known owner

It never assigns unowned or ambiguous records to an arbitrary user.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.database import normalize_database_url


def postgres_url() -> str:
    raw = os.getenv("DATABASE_URL_UNPOOLED", "").strip() or os.getenv("DATABASE_URL", "").strip()
    if not raw:
        for env_file in (BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env", BACKEND_DIR.parent / ".env.local"):
            if env_file.is_file():
                values = dotenv_values(env_file)
                raw = (values.get("DATABASE_URL_UNPOOLED") or values.get("DATABASE_URL") or "").strip()
                if raw:
                    break
    if not raw:
        print("DATABASE_URL_UNPOOLED or DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(1)
    url = normalize_database_url(raw)
    if not url.startswith("postgresql"):
        print("PostgreSQL is required.", file=sys.stderr)
        raise SystemExit(1)
    return url


def main() -> None:
    engine = create_engine(
        postgres_url(),
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    try:
        with engine.begin() as connection:
            connection.execute(text(
                'ALTER TABLE transaction_lines ADD COLUMN IF NOT EXISTS user_id INTEGER NULL'
            ))
            connection.execute(text(
                "DO $$ BEGIN "
                "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                "WHERE conname = 'fk_transaction_lines_user_id_users') THEN "
                "ALTER TABLE transaction_lines ADD CONSTRAINT fk_transaction_lines_user_id_users "
                "FOREIGN KEY (user_id) REFERENCES users(id); "
                "END IF; END $$"
            ))
            connection.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_transaction_lines_user_id '
                'ON transaction_lines (user_id)'
            ))

            result = connection.execute(text(
                "UPDATE transaction_lines AS line "
                "SET user_id = batch.user_id "
                "FROM import_batches AS batch "
                "WHERE line.import_batch_id = batch.id "
                "AND batch.user_id IS NOT NULL "
                "AND line.user_id IS NULL"
            ))
            backfilled = result.rowcount
    finally:
        engine.dispose()
    print(f"Transaction ownership migration completed; rows backfilled: {backfilled}. Unowned rows remain NULL.")


if __name__ == "__main__":
    main()
