"""
Restaurant transactions ETL.

Reads Excel (.xlsx via openpyxl) or CSV, validates/normalizes columns, rejects
invalid rows with reasons, and bulk-inserts TransactionLine rows.

Idempotent: SHA256 of file contents — if the same hash already imported with
status=success, the existing ImportBatch is reused (no duplicate lines).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ImportBatch, TransactionLine

# Canonical column -> accepted aliases (normalized: strip + lower + collapse spaces/underscores)
COLUMN_ALIASES: dict[str, set[str]] = {
    "bill_no": {"billno", "bill_no", "bill number", "bill"},
    "outlet_name": {"outlet_name", "outletname", "outlet", "outlet name"},
    "brand": {"brand"},
    "order_datetime": {
        "order_datetime",
        "orderdatetime",
        "order_date",
        "order date",
        "order_date_time",
        "datetime",
    },
    "menu_group": {"group", "menu_group", "menugroup", "category", "menu group"},
    "item": {"item", "item_name", "itemname", "product", "product_name"},
    "price": {"price", "unit_price", "unitprice", "rate"},
    "quantity": {"quantity", "qty", "qty.", "qnty"},
    "order_type": {"order_type", "ordertype", "order type", "channel"},
    "settlement": {"settlement", "payment", "payment_mode", "payment mode", "paymode"},
}

MANDATORY_COLUMNS = list(COLUMN_ALIASES.keys())

DATE_FORMATS = (
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
)

CHUNK_SIZE = 1000
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _normalize_header(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text


def map_columns(columns: list[Any]) -> dict[str, str]:
    """Map raw headers to canonical names. Raises ValueError if mandatory missing."""
    normalized = {_normalize_header(c): str(c) for c in columns}
    # Also allow looking up without underscores for alias matching
    alias_lookup: dict[str, str] = {}
    for norm, original in normalized.items():
        alias_lookup[norm] = original
        alias_lookup[norm.replace("_", "")] = original
        alias_lookup[norm.replace("_", " ")] = original

    mapping: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            key = _normalize_header(alias)
            if key in alias_lookup:
                found = alias_lookup[key]
                break
            key_compact = key.replace("_", "")
            if key_compact in alias_lookup:
                found = alias_lookup[key_compact]
                break
        if found is None:
            missing.append(canonical)
        else:
            mapping[canonical] = found

    if missing:
        raise ValueError(f"Missing mandatory columns: {', '.join(missing)}")
    return mapping


def parse_order_datetime(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "null"}:
        return None

    # Excel serial date number
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return pd.to_datetime(value, unit="D", origin="1899-12-30").to_pydatetime()
        except Exception:
            pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except Exception:
        return None


def build_order_key(bill_no: str, outlet_name: str, order_dt: datetime) -> str:
    """
    Composite order key.

    Decision: BillNo alone can collide across outlets and/or calendar days
    (shared POS sequences, multi-brand chains). Use:
        order_key = f"{bill_no}|{outlet_name}|{order_date}"
    Total Orders = COUNT(DISTINCT order_key).
    """
    order_date = order_dt.date().isoformat()
    return f"{bill_no}|{outlet_name}|{order_date}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_dataframe_from_bytes(data: bytes, filename: str) -> pd.DataFrame:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds the 50 MB limit.")
    lower = filename.lower()
    bio = BytesIO(data)
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(bio, engine="openpyxl")
    if lower.endswith(".csv"):
        return pd.read_csv(bio)
    raise ValueError("Unsupported file type. Use .xlsx or .csv")


def _read_dataframe_from_path(path: Path) -> pd.DataFrame:
    lower = path.suffix.lower()
    if lower in {".xlsx", ".xls"}:
        return pd.read_excel(path, engine="openpyxl")
    if lower == ".csv":
        return pd.read_csv(path)
    raise ValueError("Unsupported file type. Use .xlsx or .csv")


def _coerce_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none", "null", ""}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _str_or_none(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _ensure_reports_dir() -> Path:
    reports = settings.resolve_reports_dir()
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def _find_successful_batch(db: Session, file_hash: str, user_id: int | None = None) -> ImportBatch | None:
    query = db.query(ImportBatch).filter(
        ImportBatch.file_hash == file_hash,
        ImportBatch.status == "success",
    )
    if user_id is not None:
        query = query.filter(ImportBatch.user_id.in_([None, user_id]))
    return query.order_by(ImportBatch.imported_at.desc()).first()


def _validate_and_prepare_rows(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Vectorized validation suitable for ~300k rows (avoids slow iterrows)."""
    mapping = map_columns(list(df.columns))
    renamed = df.rename(columns={v: k for k, v in mapping.items()})
    renamed = renamed[MANDATORY_COLUMNS].copy()
    renamed.reset_index(drop=True, inplace=True)

    missing_counts = {col: 0 for col in MANDATORY_COLUMNS}
    valid_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    # Use object-dtype lists so None stays None (Series.map would promote None → NaN).
    dt_parsed = [parse_order_datetime(v) for v in renamed["order_datetime"].tolist()]
    price_parsed = [_coerce_float(v) for v in renamed["price"].tolist()]
    qty_parsed = [_coerce_float(v) for v in renamed["quantity"].tolist()]

    str_cols = ["bill_no", "outlet_name", "brand", "menu_group", "item", "order_type", "settlement"]
    str_parsed = {col: [_str_or_none(v) for v in renamed[col].tolist()] for col in str_cols}

    for i in range(len(renamed)):
        source_row = i + 2  # 1-based + header
        reasons: list[str] = []
        values: dict[str, Any] = {}

        order_dt = dt_parsed[i]
        if order_dt is None:
            missing_counts["order_datetime"] += 1
            reasons.append("invalid_or_missing_order_datetime")
        else:
            values["order_datetime"] = order_dt

        price = price_parsed[i]
        if price is None:
            missing_counts["price"] += 1
            reasons.append("invalid_or_missing_price")
        else:
            values["price"] = price

        qty = qty_parsed[i]
        if qty is None:
            missing_counts["quantity"] += 1
            reasons.append("invalid_or_missing_quantity")
        else:
            values["quantity"] = qty

        for col in str_cols:
            text = str_parsed[col][i]
            if text is None:
                missing_counts[col] += 1
                reasons.append(f"missing_{col}")
            else:
                values[col] = text

        if reasons:
            raw = {}
            for c in MANDATORY_COLUMNS:
                cell = renamed.at[i, c]
                raw[c] = None if pd.isna(cell) else str(cell)
            rejected.append({"source_row_number": source_row, "reasons": reasons, "raw": raw})
            continue

        price_f = float(values["price"])
        qty_f = float(values["quantity"])
        order_dt_v: datetime = values["order_datetime"]
        bill_no = str(values["bill_no"])
        outlet = str(values["outlet_name"])

        valid_rows.append(
            {
                "source_row_number": source_row,
                "bill_no": bill_no,
                "outlet_name": outlet,
                "brand": str(values["brand"]),
                "order_datetime": order_dt_v,
                "menu_group": str(values["menu_group"]),
                "item": str(values["item"]),
                "price": price_f,
                "quantity": qty_f,
                "line_revenue": price_f * qty_f,
                "order_type": str(values["order_type"]),
                "settlement": str(values["settlement"]),
                "order_key": build_order_key(bill_no, outlet, order_dt_v),
            }
        )

    return valid_rows, rejected, missing_counts


def _bulk_insert_lines(db: Session, batch_id: int, rows: list[dict[str, Any]]) -> None:
    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i : i + CHUNK_SIZE]
        db.bulk_insert_mappings(
            TransactionLine,
            [
                {
                    "import_batch_id": batch_id,
                    **row,
                }
                for row in chunk
            ],
        )
        db.flush()


def _write_report(batch: ImportBatch, rejected: list[dict[str, Any]], missing_counts: dict[str, int]) -> str:
    reports = _ensure_reports_dir()
    report_path = reports / f"import_batch_{batch.id}_{batch.file_hash[:12]}.json"
    payload = {
        "import_batch_id": batch.id,
        "filename": batch.filename,
        "file_hash": batch.file_hash,
        "status": batch.status,
        "imported_at": batch.imported_at.isoformat() if batch.imported_at else None,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "rejected_rows": batch.rejected_rows,
        "missing_values": missing_counts,
        "rejected_sample": rejected[:200],
        "notes": batch.notes,
        "reused": batch.notes == "reused_existing_import" if batch.notes else False,
    }
    report_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(report_path)


def import_restaurant_file(
    db: Session,
    *,
    file_path: str | Path | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    user_id: int | None = None,
    force: bool = False,
) -> ImportBatch:
    """
    Import restaurant transactions from a path or in-memory upload.

    Provide either file_path OR (file_bytes + filename).
    """
    if file_path is None and file_bytes is None:
        raise ValueError("Provide file_path or file_bytes")

    source_path: str | None = None
    if file_path is not None:
        path = Path(file_path)
        if not path.is_absolute():
            # Resolve relative to project root for assessment ingest convenience
            path = Path(settings.project_root) / path
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        data = path.read_bytes()
        fname = filename or path.name
        source_path = str(path)
        file_hash = sha256_bytes(data)
        df = _read_dataframe_from_path(path)
    else:
        assert file_bytes is not None
        if not filename:
            raise ValueError("filename is required when importing from bytes")
        data = file_bytes
        fname = filename
        file_hash = sha256_bytes(data)
        df = _read_dataframe_from_bytes(data, fname)

    if not force:
        existing = _find_successful_batch(db, file_hash, user_id)
        if existing:
            # Idempotent reuse — do not insert duplicate lines
            if user_id and existing.user_id is None:
                existing.user_id = user_id
                db.commit()
                db.refresh(existing)
            return existing
    else:
        # Force re-import: drop prior batches with this hash so KPIs are not double-counted
        prior = db.query(ImportBatch).filter(ImportBatch.file_hash == file_hash).all()
        for old in prior:
            db.delete(old)
        db.flush()

    batch = ImportBatch(
        filename=fname,
        file_hash=file_hash,
        imported_at=datetime.utcnow(),
        status="processing",
        total_rows=0,
        valid_rows=0,
        rejected_rows=0,
        missing_values_json="{}",
        source_path=source_path,
        user_id=user_id,
        notes=None,
    )
    db.add(batch)
    db.flush()

    try:
        if df.empty:
            raise ValueError("File contains no data rows.")

        valid_rows, rejected, missing_counts = _validate_and_prepare_rows(df)
        batch.total_rows = len(df)
        batch.valid_rows = len(valid_rows)
        batch.rejected_rows = len(rejected)
        batch.missing_values_json = json.dumps(missing_counts)

        _bulk_insert_lines(db, batch.id, valid_rows)
        batch.status = "success" if valid_rows else "failed"
        if not valid_rows:
            batch.notes = "No valid rows after validation."
        report_path = _write_report(batch, rejected, missing_counts)
        batch.error_report_path = report_path
        db.commit()
        db.refresh(batch)
        return batch
    except Exception as exc:
        db.rollback()
        # Re-attach a failed batch record after rollback for auditability
        failed = ImportBatch(
            filename=fname,
            file_hash=file_hash,
            imported_at=datetime.utcnow(),
            status="failed",
            total_rows=getattr(batch, "total_rows", 0) or 0,
            valid_rows=getattr(batch, "valid_rows", 0) or 0,
            rejected_rows=getattr(batch, "rejected_rows", 0) or 0,
            missing_values_json=getattr(batch, "missing_values_json", "{}") or "{}",
            source_path=source_path,
            user_id=user_id,
            notes=str(exc)[:2000],
        )
        db.add(failed)
        try:
            db.flush()
            report_path = _write_report(failed, [], json.loads(failed.missing_values_json or "{}"))
            failed.error_report_path = report_path
            db.commit()
            db.refresh(failed)
        except Exception:
            db.rollback()
        raise


def import_from_default_path(db: Session, user_id: int | None = None, path: str | None = None) -> ImportBatch:
    target = Path(path) if path else settings.resolve_restaurant_source_path()
    return import_restaurant_file(db, file_path=target, user_id=user_id)
