"""CB 360 restaurant analytics API — all routes require JWT auth."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.etl import MAX_UPLOAD_BYTES, import_restaurant_file
from app.models import User
from app.restaurant_analytics import (
    FilterParams,
    business_insights,
    export_csv_query,
    filter_options,
    get_kpis,
    import_summary,
    order_type_analytics,
    product_contribution,
    product_table,
    revenue_by_brand,
    revenue_by_category,
    revenue_by_outlet,
    revenue_trend,
    settlement_analytics,
    settlement_by_outlet,
    top_items,
    transactions_page,
)
from app.routers.auth import get_current_user
from app.schemas import ImportFromPathRequest

router = APIRouter(prefix="/restaurant", tags=["restaurant"])


def _parse_dt(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            if fmt in {"%Y-%m-%d", "%d-%m-%Y"} and end_of_day:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Invalid date format: {value}")


def _filters(
    date_from: str | None = None,
    date_to: str | None = None,
    brand: str | None = None,
    outlet: str | None = None,
    menu_group: str | None = None,
    order_type: str | None = None,
    settlement: str | None = None,
) -> FilterParams:
    return FilterParams(
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to, end_of_day=True),
        brand=brand or None,
        outlet=outlet or None,
        menu_group=menu_group or None,
        order_type=order_type or None,
        settlement=settlement or None,
    )


def _ok(data, started: float) -> dict:
    return {"data": data, "meta": {"query_ms": round((time.perf_counter() - started) * 1000, 2)}}


@router.get("/kpis")
def kpis(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = get_kpis(db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement))
    return _ok(data, started)


@router.get("/trends")
def trends(
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = revenue_trend(
        db,
        _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement),
        granularity=granularity,
    )
    return _ok(data, started)


@router.get("/outlets")
def outlets(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = revenue_by_outlet(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )
    return _ok(data, started)


@router.get("/brands")
def brands(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = revenue_by_brand(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )
    return _ok(data, started)


@router.get("/categories")
def categories(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = revenue_by_category(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )
    return _ok(data, started)


@router.get("/products")
def products(
    search: str = Query(""),
    sort: str = Query("revenue"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(10, ge=1, le=100),
    contribution: bool = Query(False),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    filters = _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    if contribution:
        data = {
            "top_items": top_items(db, filters, limit=limit),
            "contribution": product_contribution(db, filters, limit=limit),
        }
    else:
        data = product_table(db, filters, search=search, sort=sort, page=page, page_size=page_size)
    return _ok(data, started)


@router.get("/order-types")
def order_types(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = order_type_analytics(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )
    return _ok(data, started)


@router.get("/settlements")
def settlements(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    filters = _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    data = {
        "distribution": settlement_analytics(db, filters),
        "outlet_wise": settlement_by_outlet(db, filters),
    }
    return _ok(data, started)


@router.get("/transactions")
def transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = transactions_page(
        db,
        _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement),
        page=page,
        page_size=page_size,
    )
    return _ok(data, started)


@router.get("/filters")
def filters_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    return _ok(filter_options(db), started)


@router.get("/insights")
def insights(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    data = business_insights(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )
    return _ok(data, started)


@router.get("/imports")
def imports_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    return _ok(import_summary(db, current_user.id), started)


@router.post("/imports/from-path")
def imports_from_path(
    payload: ImportFromPathRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    try:
        target = payload.path or str(settings.resolve_restaurant_source_path())
        path = Path(target)
        if not path.is_absolute():
            path = Path(settings.project_root) / path
        batch = import_restaurant_file(
            db,
            file_path=path,
            user_id=current_user.id,
            force=payload.force,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Import failed. Check the source file format.") from None

    data = {
        "id": batch.id,
        "filename": batch.filename,
        "file_hash": batch.file_hash,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "rejected_rows": batch.rejected_rows,
        "error_report_path": batch.error_report_path,
        "notes": batch.notes,
    }
    return _ok(data, started)


@router.post("/imports/upload")
async def imports_upload(
    file: UploadFile = File(...),
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    lower = file.filename.lower()
    if not (lower.endswith(".xlsx") or lower.endswith(".xls") or lower.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .csv files are allowed.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 50 MB limit.")

    try:
        batch = import_restaurant_file(
            db,
            file_bytes=content,
            filename=file.filename,
            user_id=current_user.id,
            force=force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Import failed. Check the file format.") from None

    data = {
        "id": batch.id,
        "filename": batch.filename,
        "file_hash": batch.file_hash,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "rejected_rows": batch.rejected_rows,
        "error_report_path": batch.error_report_path,
        "notes": batch.notes,
    }
    return _ok(data, started)


@router.get("/export.csv")
def export_csv(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    brand: str | None = Query(None),
    outlet: str | None = Query(None),
    menu_group: str | None = Query(None),
    order_type: str | None = Query(None),
    settlement: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    csv_text, _n = export_csv_query(
        db, _filters(date_from, date_to, brand, outlet, menu_group, order_type, settlement)
    )

    def iter_chunks():
        yield csv_text

    return StreamingResponse(
        iter_chunks(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=restaurant_export.csv"},
    )


@router.get("/health-metrics")
def health_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    kpis = get_kpis(db, FilterParams())
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    return _ok(
        {
            "status": "ok",
            "kpi_query_ms": elapsed,
            "total_transactions": kpis["total_transactions"],
            "total_orders": kpis["total_orders"],
        },
        started,
    )
