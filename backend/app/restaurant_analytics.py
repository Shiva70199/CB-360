"""
Server-side restaurant analytics.

All aggregations run in SQL via SQLAlchemy. Never load the full transaction
table into pandas for API responses.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Query, Session

from app.models import ImportBatch, TransactionLine


@dataclass
class FilterParams:
    date_from: datetime | None = None
    date_to: datetime | None = None
    brand: str | None = None
    outlet: str | None = None
    menu_group: str | None = None
    order_type: str | None = None
    settlement: str | None = None


def _apply_filters(query: Query, filters: FilterParams) -> Query:
    if filters.date_from is not None:
        query = query.filter(TransactionLine.order_datetime >= filters.date_from)
    if filters.date_to is not None:
        query = query.filter(TransactionLine.order_datetime <= filters.date_to)
    if filters.brand:
        query = query.filter(TransactionLine.brand == filters.brand)
    if filters.outlet:
        query = query.filter(TransactionLine.outlet_name == filters.outlet)
    if filters.menu_group:
        query = query.filter(TransactionLine.menu_group == filters.menu_group)
    if filters.order_type:
        query = query.filter(TransactionLine.order_type == filters.order_type)
    if filters.settlement:
        query = query.filter(TransactionLine.settlement == filters.settlement)
    return query


def _base_query(db: Session, filters: FilterParams) -> Query:
    return _apply_filters(db.query(TransactionLine), filters)


def _period_kpis(db: Session, filters: FilterParams) -> dict[str, Any]:
    q = _base_query(db, filters)
    row = q.with_entities(
        func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("total_revenue"),
        func.count(func.distinct(TransactionLine.order_key)).label("total_orders"),
        func.coalesce(func.sum(TransactionLine.quantity), 0.0).label("total_items_sold"),
        func.count(TransactionLine.id).label("total_transactions"),
        func.count(func.distinct(TransactionLine.outlet_name)).label("active_outlets"),
    ).one()

    total_revenue = float(row.total_revenue or 0)
    total_orders = int(row.total_orders or 0)
    aov = (total_revenue / total_orders) if total_orders else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "aov": round(aov, 2),
        "total_items_sold": float(row.total_items_sold or 0),
        "total_transactions": int(row.total_transactions or 0),
        "active_outlets": int(row.active_outlets or 0),
    }


def _growth(current: float, previous: float) -> float | None:
    # Only report growth when a prior period had activity (avoid invented %).
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100.0, 2)


def get_kpis(db: Session, filters: FilterParams) -> dict[str, Any]:
    current = _period_kpis(db, filters)
    result = {**current, "comparison": None}

    # Optional comparison period only when an explicit date range is provided
    if filters.date_from is not None and filters.date_to is not None:
        span = filters.date_to - filters.date_from
        if span.total_seconds() >= 0:
            prev_to = filters.date_from - timedelta(seconds=1)
            prev_from = prev_to - span
            prev_filters = FilterParams(
                date_from=prev_from,
                date_to=prev_to,
                brand=filters.brand,
                outlet=filters.outlet,
                menu_group=filters.menu_group,
                order_type=filters.order_type,
                settlement=filters.settlement,
            )
            previous = _period_kpis(db, prev_filters)
            result["comparison"] = {
                "previous": previous,
                "growth": {
                    "total_revenue_pct": _growth(current["total_revenue"], previous["total_revenue"]),
                    "total_orders_pct": _growth(float(current["total_orders"]), float(previous["total_orders"])),
                    "aov_pct": _growth(current["aov"], previous["aov"]),
                },
            }
    return result


def revenue_trend(db: Session, filters: FilterParams, granularity: str = "day") -> list[dict[str, Any]]:
    gran = (granularity or "day").lower()
    if gran not in {"day", "week", "month"}:
        gran = "day"

    # SQLite-friendly date truncation via strftime
    if gran == "day":
        bucket = func.strftime("%Y-%m-%d", TransactionLine.order_datetime)
    elif gran == "week":
        # ISO-like week key: year-week
        bucket = func.strftime("%Y-W%W", TransactionLine.order_datetime)
    else:
        bucket = func.strftime("%Y-%m", TransactionLine.order_datetime)

    q = (
        _base_query(db, filters)
        .with_entities(
            bucket.label("period"),
            func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
            func.count(func.distinct(TransactionLine.order_key)).label("orders"),
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    return [
        {
            "period": r.period,
            "revenue": round(float(r.revenue or 0), 2),
            "orders": int(r.orders or 0),
        }
        for r in q.all()
    ]


def _group_revenue(db: Session, filters: FilterParams, column) -> list[dict[str, Any]]:
    q = (
        _base_query(db, filters)
        .with_entities(
            column.label("name"),
            func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
            func.count(func.distinct(TransactionLine.order_key)).label("orders"),
            func.coalesce(func.sum(TransactionLine.quantity), 0.0).label("items_sold"),
        )
        .group_by(column)
        .order_by(desc("revenue"))
    )
    rows = []
    for r in q.all():
        revenue = float(r.revenue or 0)
        orders = int(r.orders or 0)
        rows.append(
            {
                "name": r.name,
                "revenue": round(revenue, 2),
                "orders": orders,
                "aov": round(revenue / orders, 2) if orders else 0.0,
                "items_sold": float(r.items_sold or 0),
            }
        )
    return rows


def revenue_by_outlet(db: Session, filters: FilterParams) -> list[dict[str, Any]]:
    return _group_revenue(db, filters, TransactionLine.outlet_name)


def revenue_by_brand(db: Session, filters: FilterParams) -> list[dict[str, Any]]:
    return _group_revenue(db, filters, TransactionLine.brand)


def revenue_by_category(db: Session, filters: FilterParams) -> list[dict[str, Any]]:
    return _group_revenue(db, filters, TransactionLine.menu_group)


def top_items(db: Session, filters: FilterParams, limit: int = 10) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    q = (
        _base_query(db, filters)
        .with_entities(
            TransactionLine.item.label("item"),
            TransactionLine.menu_group.label("menu_group"),
            func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
            func.coalesce(func.sum(TransactionLine.quantity), 0.0).label("quantity"),
        )
        .group_by(TransactionLine.item, TransactionLine.menu_group)
        .order_by(desc("revenue"))
        .limit(limit)
    )
    return [
        {
            "item": r.item,
            "menu_group": r.menu_group,
            "revenue": round(float(r.revenue or 0), 2),
            "quantity": float(r.quantity or 0),
        }
        for r in q.all()
    ]


def product_contribution(db: Session, filters: FilterParams, limit: int = 20) -> list[dict[str, Any]]:
    total_rev = (
        _base_query(db, filters)
        .with_entities(func.coalesce(func.sum(TransactionLine.line_revenue), 0.0))
        .scalar()
    )
    total_rev = float(total_rev or 0)
    items = top_items(db, filters, limit=limit)
    for row in items:
        row["contribution_pct"] = round((row["revenue"] / total_rev) * 100.0, 2) if total_rev else 0.0
    return items


def order_type_analytics(db: Session, filters: FilterParams) -> dict[str, Any]:
    by_type = _group_revenue(db, filters, TransactionLine.order_type)
    distribution = [
        {"name": r["name"], "orders": r["orders"], "revenue": r["revenue"], "aov": r["aov"]}
        for r in by_type
    ]

    # Outlet-wise order type revenue
    q = (
        _base_query(db, filters)
        .with_entities(
            TransactionLine.outlet_name.label("outlet"),
            TransactionLine.order_type.label("order_type"),
            func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
            func.count(func.distinct(TransactionLine.order_key)).label("orders"),
        )
        .group_by(TransactionLine.outlet_name, TransactionLine.order_type)
        .order_by(TransactionLine.outlet_name, desc("revenue"))
    )
    outlet_wise = [
        {
            "outlet": r.outlet,
            "order_type": r.order_type,
            "revenue": round(float(r.revenue or 0), 2),
            "orders": int(r.orders or 0),
        }
        for r in q.all()
    ]
    return {"distribution": distribution, "outlet_wise": outlet_wise}


def settlement_analytics(db: Session, filters: FilterParams) -> list[dict[str, Any]]:
    return _group_revenue(db, filters, TransactionLine.settlement)


def settlement_by_outlet(db: Session, filters: FilterParams) -> list[dict[str, Any]]:
    q = (
        _base_query(db, filters)
        .with_entities(
            TransactionLine.outlet_name.label("outlet"),
            TransactionLine.settlement.label("settlement"),
            func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
            func.count(func.distinct(TransactionLine.order_key)).label("orders"),
        )
        .group_by(TransactionLine.outlet_name, TransactionLine.settlement)
        .order_by(TransactionLine.outlet_name, desc("revenue"))
    )
    return [
        {
            "outlet": r.outlet,
            "settlement": r.settlement,
            "revenue": round(float(r.revenue or 0), 2),
            "orders": int(r.orders or 0),
        }
        for r in q.all()
    ]


def product_table(
    db: Session,
    filters: FilterParams,
    *,
    search: str = "",
    sort: str = "revenue",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    sort_key = (sort or "revenue").lower()

    q = _base_query(db, filters)
    if search.strip():
        like = f"%{search.strip()}%"
        q = q.filter(
            or_(
                TransactionLine.item.ilike(like),
                TransactionLine.menu_group.ilike(like),
            )
        )

    grouped = q.with_entities(
        TransactionLine.item.label("item"),
        TransactionLine.menu_group.label("menu_group"),
        func.coalesce(func.sum(TransactionLine.line_revenue), 0.0).label("revenue"),
        func.coalesce(func.sum(TransactionLine.quantity), 0.0).label("quantity"),
        func.avg(TransactionLine.price).label("avg_price"),
    ).group_by(TransactionLine.item, TransactionLine.menu_group)

    sub = grouped.subquery()
    total = db.query(func.count()).select_from(sub).scalar() or 0

    ascending = sort_key.endswith("_asc") or sort_key in {"item", "quantity_asc", "revenue_asc"}
    normalized_sort = sort_key.replace("_asc", "").replace("_desc", "")
    sort_map = {
        "revenue": sub.c.revenue,
        "quantity": sub.c.quantity,
        "item": sub.c.item,
        "avg_price": sub.c.avg_price,
    }
    order_col = sort_map.get(normalized_sort, sub.c.revenue)
    if ascending or normalized_sort == "item":
        rows_q = db.query(sub).order_by(order_col.asc())
    else:
        rows_q = db.query(sub).order_by(order_col.desc())

    rows = rows_q.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "item": r.item,
            "menu_group": r.menu_group,
            "revenue": round(float(r.revenue or 0), 2),
            "quantity": float(r.quantity or 0),
            "avg_price": round(float(r.avg_price or 0), 2),
        }
        for r in rows
    ]
    total_pages = max(1, (int(total) + page_size - 1) // page_size) if total else 1
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def transactions_page(
    db: Session,
    filters: FilterParams,
    *,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    q = _base_query(db, filters)
    total = q.count()
    rows = (
        q.order_by(TransactionLine.order_datetime.desc(), TransactionLine.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "bill_no": r.bill_no,
            "outlet_name": r.outlet_name,
            "brand": r.brand,
            "order_datetime": r.order_datetime.isoformat() if r.order_datetime else None,
            "menu_group": r.menu_group,
            "item": r.item,
            "price": r.price,
            "quantity": r.quantity,
            "line_revenue": r.line_revenue,
            "order_type": r.order_type,
            "settlement": r.settlement,
            "order_key": r.order_key,
        }
        for r in rows
    ]
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def filter_options(db: Session) -> dict[str, Any]:
    def distinct(col) -> list[str]:
        rows = (
            db.query(col)
            .filter(col.isnot(None))
            .distinct()
            .order_by(col)
            .all()
        )
        return [r[0] for r in rows if r[0] is not None]

    date_bounds = db.query(
        func.min(TransactionLine.order_datetime),
        func.max(TransactionLine.order_datetime),
    ).one()
    return {
        "brands": distinct(TransactionLine.brand),
        "outlets": distinct(TransactionLine.outlet_name),
        "menu_groups": distinct(TransactionLine.menu_group),
        "order_types": distinct(TransactionLine.order_type),
        "settlements": distinct(TransactionLine.settlement),
        "date_min": date_bounds[0].isoformat() if date_bounds[0] else None,
        "date_max": date_bounds[1].isoformat() if date_bounds[1] else None,
    }


def import_summary(db: Session) -> list[dict[str, Any]]:
    batches = db.query(ImportBatch).order_by(ImportBatch.imported_at.desc()).all()
    result = []
    for b in batches:
        missing = {}
        try:
            missing = json.loads(b.missing_values_json or "{}")
        except json.JSONDecodeError:
            missing = {}
        result.append(
            {
                "id": b.id,
                "filename": b.filename,
                "file_hash": b.file_hash,
                "imported_at": b.imported_at.isoformat() if b.imported_at else None,
                "status": b.status,
                "total_rows": b.total_rows,
                "valid_rows": b.valid_rows,
                "rejected_rows": b.rejected_rows,
                "missing_values": missing,
                "error_report_path": b.error_report_path,
                "source_path": b.source_path,
                "notes": b.notes,
            }
        )
    return result


def business_insights(db: Session, filters: FilterParams) -> list[dict[str, str]]:
    """Derive short insights from real aggregates only — no invented numbers."""
    insights: list[dict[str, str]] = []
    kpis = get_kpis(db, filters)
    if kpis["total_transactions"] == 0:
        return [
            {
                "title": "No data",
                "detail": "Import restaurant transactions to generate insights.",
            }
        ]

    insights.append(
        {
            "title": "Revenue overview",
            "detail": (
                f"Total revenue is {kpis['total_revenue']:.2f} across "
                f"{kpis['total_orders']} orders (AOV {kpis['aov']:.2f})."
            ),
        }
    )

    outlets = revenue_by_outlet(db, filters)
    if outlets:
        top = outlets[0]
        insights.append(
            {
                "title": "Top outlet",
                "detail": (
                    f"{top['name']} leads with revenue {top['revenue']:.2f} "
                    f"and {top['orders']} orders."
                ),
            }
        )

    categories = revenue_by_category(db, filters)
    if categories:
        top_cat = categories[0]
        insights.append(
            {
                "title": "Top category",
                "detail": (
                    f"{top_cat['name']} contributes {top_cat['revenue']:.2f} in revenue."
                ),
            }
        )

    order_types = order_type_analytics(db, filters)["distribution"]
    if order_types:
        lead = order_types[0]
        insights.append(
            {
                "title": "Leading order type",
                "detail": (
                    f"{lead['name']} accounts for {lead['orders']} orders "
                    f"and {lead['revenue']:.2f} revenue."
                ),
            }
        )

    items = top_items(db, filters, limit=1)
    if items:
        insights.append(
            {
                "title": "Best seller",
                "detail": (
                    f"{items[0]['item']} generated {items[0]['revenue']:.2f} "
                    f"from {items[0]['quantity']:.0f} units sold."
                ),
            }
        )

    if kpis.get("comparison") and kpis["comparison"].get("growth"):
        g = kpis["comparison"]["growth"]
        rev_g = g.get("total_revenue_pct")
        if rev_g is not None:
            direction = "up" if rev_g >= 0 else "down"
            insights.append(
                {
                    "title": "Period comparison",
                    "detail": f"Revenue is {direction} {abs(rev_g):.2f}% vs the prior period.",
                }
            )

    return insights


EXPORT_ROW_CAP = 50_000


def export_csv_query(db: Session, filters: FilterParams, cap: int = EXPORT_ROW_CAP) -> tuple[str, int]:
    """Return CSV text for filtered lines, capped to avoid huge downloads."""
    q = _base_query(db, filters).order_by(TransactionLine.order_datetime.asc(), TransactionLine.id.asc())
    rows = q.limit(cap).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "bill_no",
            "outlet_name",
            "brand",
            "order_datetime",
            "menu_group",
            "item",
            "price",
            "quantity",
            "line_revenue",
            "order_type",
            "settlement",
            "order_key",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.bill_no,
                r.outlet_name,
                r.brand,
                r.order_datetime.isoformat() if r.order_datetime else "",
                r.menu_group,
                r.item,
                r.price,
                r.quantity,
                r.line_revenue,
                r.order_type,
                r.settlement,
                r.order_key,
            ]
        )
    return buf.getvalue(), len(rows)
