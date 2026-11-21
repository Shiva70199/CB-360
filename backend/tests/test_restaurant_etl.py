"""ETL unit tests for restaurant import (tiny fixture only)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.etl import (
    build_order_key,
    import_restaurant_file,
    map_columns,
    parse_order_datetime,
)
from app.models import ImportBatch, TransactionLine  # noqa: F401 — register tables


FIXTURE_CSV = """BillNo,Outlet_Name,Brand,Order_Datetime,Group,Item,Price,Quantity,Order_Type,Settlement
B100,Downtown,CafeOne,15-01-2024 12:30:00,Beverages,Latte,120,2,Dine-In,Card
B100,Downtown,CafeOne,15-01-2024 12:30:00,Food,Sandwich,180,1,Dine-In,Card
B100,Airport,CafeOne,15-01-2024 18:00:00,Beverages,Espresso,90,1,Takeaway,Cash
B200,Downtown,BiteBrand,16-01-2024 09:15:00,Food,Burger,250,2,Delivery,UPI
B300,Downtown,CafeOne,16-01-2024 10:00:00,Food,Fries,,1,Dine-In,Cash
"""


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("app.config.settings.reports_dir", str(reports))
    monkeypatch.setattr("app.etl.settings.reports_dir", str(reports))
    monkeypatch.setattr("app.config.settings.project_root", str(tmp_path))
    monkeypatch.setattr("app.etl.settings.project_root", str(tmp_path))

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestColumnMappingAndDates:
    def test_map_columns_aliases(self):
        mapping = map_columns(
            ["Bill No", "Outlet", "Brand", "Order Date", "Category", "Product", "Rate", "Qty", "Channel", "Payment"]
        )
        assert mapping["bill_no"]
        assert mapping["outlet_name"]
        assert mapping["menu_group"]
        assert mapping["item"]
        assert mapping["price"]
        assert mapping["quantity"]
        assert mapping["order_type"]
        assert mapping["settlement"]

    def test_map_columns_missing_raises(self):
        with pytest.raises(ValueError, match="Missing mandatory"):
            map_columns(["BillNo", "Brand"])

    def test_parse_dd_mm_yyyy(self):
        dt = parse_order_datetime("15-01-2024 12:30:00")
        assert dt == datetime(2024, 1, 15, 12, 30, 0)

    def test_parse_fallback_slash(self):
        dt = parse_order_datetime("15/01/2024 12:30:00")
        assert dt == datetime(2024, 1, 15, 12, 30, 0)

    def test_order_key_composite(self):
        key = build_order_key("B100", "Downtown", datetime(2024, 1, 15, 12, 30))
        assert key == "B100|Downtown|2024-01-15"


class TestImportRestaurantFile:
    def test_shared_bill_counts_as_one_order(self, db_session):
        batch = import_restaurant_file(
            db_session,
            file_bytes=FIXTURE_CSV.encode("utf-8"),
            filename="fixture.csv",
            user_id=1,
        )
        assert batch.status == "success"
        assert batch.valid_rows == 4
        assert batch.rejected_rows == 1

        distinct_orders = (
            db_session.query(TransactionLine.order_key).distinct().count()
        )
        # B100 Downtown, B100 Airport, B200 Downtown
        assert distinct_orders == 3

        # Multiple lines share B100|Downtown|2024-01-15
        downtown_b100 = (
            db_session.query(TransactionLine)
            .filter(TransactionLine.order_key == "B100|Downtown|2024-01-15")
            .count()
        )
        assert downtown_b100 == 2

    def test_revenue_is_price_times_qty(self, db_session):
        import_restaurant_file(
            db_session,
            file_bytes=FIXTURE_CSV.encode("utf-8"),
            filename="fixture.csv",
        )
        total = db_session.query(func.sum(TransactionLine.line_revenue)).scalar()
        # (120*2)+(180*1)+(90*1)+(250*2) = 1010
        assert float(total) == 1010.0

        for line in db_session.query(TransactionLine).all():
            assert line.line_revenue == pytest.approx(line.price * line.quantity)

    def test_missing_invalid_handling(self, db_session):
        batch = import_restaurant_file(
            db_session,
            file_bytes=FIXTURE_CSV.encode("utf-8"),
            filename="fixture.csv",
        )
        assert batch.rejected_rows == 1
        missing = json.loads(batch.missing_values_json)
        assert missing.get("price", 0) >= 1
        assert batch.error_report_path
        assert Path(batch.error_report_path).exists()

    def test_idempotent_by_hash(self, db_session):
        b1 = import_restaurant_file(
            db_session,
            file_bytes=FIXTURE_CSV.encode("utf-8"),
            filename="fixture.csv",
        )
        b2 = import_restaurant_file(
            db_session,
            file_bytes=FIXTURE_CSV.encode("utf-8"),
            filename="fixture.csv",
        )
        assert b1.id == b2.id
        assert db_session.query(TransactionLine).count() == 4
        assert db_session.query(ImportBatch).count() == 1

    def test_import_from_path(self, db_session, tmp_path):
        path = tmp_path / "sample.csv"
        path.write_text(FIXTURE_CSV, encoding="utf-8")
        batch = import_restaurant_file(db_session, file_path=path)
        assert batch.status == "success"
        assert batch.valid_rows == 4
