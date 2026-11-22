"""Restaurant analytics API tests using a tiny imported fixture (no fake UI metrics)."""

from __future__ import annotations

import io
import os
import sys

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base, get_db
from app.main import app
from app.models import ImportBatch, TransactionLine  # noqa: F401
from app.storage import load_private_object

FIXTURE_CSV = """BillNo,Outlet_Name,Brand,Order_Datetime,Group,Item,Price,Quantity,Order_Type,Settlement
B100,Downtown,CafeOne,15-01-2024 12:30:00,Beverages,Latte,120,2,Dine-In,Card
B100,Downtown,CafeOne,15-01-2024 12:30:00,Food,Sandwich,180,1,Dine-In,Card
B100,Airport,CafeOne,15-01-2024 18:00:00,Beverages,Espresso,90,1,Takeaway,Cash
B200,Downtown,BiteBrand,16-01-2024 09:15:00,Food,Burger,250,2,Delivery,UPI
B300,Downtown,CafeOne,16-01-2024 10:00:00,Food,Fries,,1,Dine-In,Cash
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()

    monkeypatch.setattr("app.config.settings.upload_dir", str(upload_dir))
    monkeypatch.setattr("app.services.settings.upload_dir", str(upload_dir))
    monkeypatch.setattr("app.storage.settings.upload_dir", str(upload_dir))
    monkeypatch.setattr("app.config.settings.storage_backend", "local")
    monkeypatch.setattr("app.config.settings.reports_dir", str(reports))
    monkeypatch.setattr("app.etl.settings.reports_dir", str(reports))
    monkeypatch.setattr("app.config.settings.project_root", str(tmp_path))
    monkeypatch.setattr("app.etl.settings.project_root", str(tmp_path))

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client, email="rest@example.com", password="secret123"):
    client.post("/auth/register", json={"email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def import_fixture(client, headers):
    res = client.post(
        "/restaurant/imports/upload",
        headers=headers,
        files={"file": ("fixture.csv", io.BytesIO(FIXTURE_CSV.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "data" in body
    assert body["data"]["status"] == "success"
    assert body["data"]["valid_rows"] == 4
    assert body["data"]["rejected_rows"] == 1
    return body["data"]


class TestRestaurantAnalyticsApi:
    def test_requires_auth(self, client):
        assert client.get("/restaurant/kpis").status_code == 401

    def test_empty_kpis_are_zeros(self, client):
        headers = register_and_login(client, "empty@test.com")
        res = client.get("/restaurant/kpis", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_revenue"] == 0
        assert data["total_orders"] == 0
        assert data["aov"] == 0
        assert data["total_transactions"] == 0
        assert data["comparison"] is None

    def test_kpis_from_imported_fixture(self, client):
        headers = register_and_login(client, "kpi@test.com")
        import_fixture(client, headers)

        res = client.get("/restaurant/kpis", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        # Not hardcoded defaults — derived from fixture
        assert data["total_revenue"] == 1010.0
        assert data["total_orders"] == 3
        assert data["total_transactions"] == 4
        assert data["aov"] == pytest.approx(1010.0 / 3, rel=1e-3)
        assert data["total_items_sold"] == 6.0  # 2+1+1+2
        assert data["active_outlets"] == 2
        assert "meta" in res.json()
        assert "query_ms" in res.json()["meta"]

    def test_shared_bill_one_order_via_api(self, client):
        headers = register_and_login(client, "orders@test.com")
        import_fixture(client, headers)
        data = client.get("/restaurant/kpis", headers=headers).json()["data"]
        assert data["total_orders"] == 3
        assert data["total_transactions"] == 4

    def test_trends_and_breakdowns(self, client):
        headers = register_and_login(client, "trend@test.com")
        import_fixture(client, headers)

        trends = client.get("/restaurant/trends?granularity=day", headers=headers).json()["data"]
        assert len(trends) >= 2
        assert sum(t["revenue"] for t in trends) == pytest.approx(1010.0)

        outlets = client.get("/restaurant/outlets", headers=headers).json()["data"]
        names = {o["name"] for o in outlets}
        assert "Downtown" in names
        assert "Airport" in names

        brands = client.get("/restaurant/brands", headers=headers).json()["data"]
        assert {b["name"] for b in brands} >= {"CafeOne", "BiteBrand"}

        cats = client.get("/restaurant/categories", headers=headers).json()["data"]
        assert {c["name"] for c in cats} >= {"Beverages", "Food"}

    def test_products_and_transactions_pagination(self, client):
        headers = register_and_login(client, "page@test.com")
        import_fixture(client, headers)

        products = client.get("/restaurant/products?page=1&page_size=2", headers=headers).json()["data"]
        assert products["page"] == 1
        assert products["page_size"] == 2
        assert products["total"] >= 2
        assert len(products["items"]) == 2

        txns = client.get("/restaurant/transactions?page=1&page_size=2", headers=headers).json()["data"]
        assert txns["total"] == 4
        assert len(txns["items"]) == 2

    def test_filters_order_types_settlements_insights(self, client):
        headers = register_and_login(client, "filt@test.com")
        import_fixture(client, headers)

        filters = client.get("/restaurant/filters", headers=headers).json()["data"]
        assert "Downtown" in filters["outlets"]
        assert "CafeOne" in filters["brands"]

        ot = client.get("/restaurant/order-types", headers=headers).json()["data"]
        assert "distribution" in ot
        assert len(ot["distribution"]) >= 1

        st = client.get("/restaurant/settlements", headers=headers).json()["data"]
        assert "distribution" in st
        assert len(st["distribution"]) >= 1
        assert "outlet_wise" in st

        insights = client.get("/restaurant/insights", headers=headers).json()["data"]
        assert isinstance(insights, list)
        assert len(insights) >= 1
        # Insights mention real revenue figure from fixture
        joined = " ".join(i["detail"] for i in insights)
        assert "1010" in joined

    def test_imports_list_and_export(self, client):
        headers = register_and_login(client, "imp@test.com")
        import_fixture(client, headers)

        imports = client.get("/restaurant/imports", headers=headers).json()["data"]
        assert len(imports) >= 1
        assert imports[0]["valid_rows"] == 4

        export = client.get("/restaurant/export.csv", headers=headers)
        assert export.status_code == 200
        assert "text/csv" in export.headers["content-type"]
        assert "bill_no" in export.text.lower()
        assert "Latte" in export.text

    def test_xlsx_upload_persists_and_updates_analytics(self, client):
        headers = register_and_login(client, "xlsx-import@test.com")
        data = pd.DataFrame(
            [
                {
                    "BillNo": "XLSX-1",
                    "Outlet_Name": "Excel Outlet",
                    "Brand": "CB360",
                    "Order_Datetime": "2024-01-15 12:30:00",
                    "Group": "Food",
                    "Item": "Excel Meal",
                    "Price": 250,
                    "Quantity": 2,
                    "Order_Type": "Dine-In",
                    "Settlement": "Card",
                }
            ]
        )
        content = io.BytesIO()
        data.to_excel(content, index=False, engine="openpyxl")
        content.seek(0)
        response = client.post(
            "/restaurant/imports/upload",
            headers=headers,
            files={
                "file": (
                    "restaurant.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["valid_rows"] == 1
        assert client.get("/restaurant/kpis", headers=headers).json()["data"]["total_revenue"] == 500.0

    def test_upload_30000_csv_persists_history_and_analytics(self, client):
        headers = register_and_login(client, "large-import@test.com")
        lines = ["BillNo,Outlet_Name,Brand,Order_Datetime,Group,Item,Price,Quantity,Order_Type,Settlement"]
        lines.extend(
            f"B{i:05d},Outlet{i % 10},CB360,2024-01-15 12:{i % 60:02d}:00,Food,Item{i % 20},{100 + i % 10},1,Dine-In,Card"
            for i in range(30000)
        )
        original = ("\n".join(lines) + "\n").encode("utf-8")
        response = client.post(
            "/restaurant/imports/upload",
            headers=headers,
            files={"file": ("large-30000.csv", io.BytesIO(original), "text/csv")},
        )
        assert response.status_code == 200, response.text
        batch = response.json()["data"]
        assert batch["total_rows"] == batch["valid_rows"] == 30000
        assert batch["rejected_rows"] == 0

        history = client.get("/restaurant/imports", headers=headers).json()["data"]
        assert [item["id"] for item in history] == [batch["id"]]
        assert load_private_object(history[0]["source_path"]) == original

        kpis = client.get("/restaurant/kpis", headers=headers).json()["data"]
        assert kpis["total_transactions"] == 30000
        transactions = client.get("/restaurant/transactions?page_size=10", headers=headers).json()["data"]
        assert transactions["total"] == 30000
        assert len(transactions["items"]) == 10
        assert client.get("/restaurant/trends", headers=headers).status_code == 200

    def test_health_metrics(self, client):
        headers = register_and_login(client, "health@test.com")
        import_fixture(client, headers)
        res = client.get("/restaurant/health-metrics", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "ok"
        assert data["total_orders"] == 3

    def test_filter_by_outlet(self, client):
        headers = register_and_login(client, "outletf@test.com")
        import_fixture(client, headers)
        data = client.get("/restaurant/kpis?outlet=Airport", headers=headers).json()["data"]
        assert data["total_revenue"] == 90.0
        assert data["total_orders"] == 1
        assert data["total_transactions"] == 1

    def test_imports_reports_and_analytics_are_isolated_by_user(self, client):
        owner_headers = register_and_login(client, "isolated-owner@test.com")
        other_headers = register_and_login(client, "isolated-other@test.com")
        owner_batch = import_fixture(client, owner_headers)

        other_file = FIXTURE_CSV.replace("Latte", "OtherUserItem")
        response = client.post(
            "/restaurant/imports/upload",
            headers=other_headers,
            files={"file": ("other.csv", io.BytesIO(other_file.encode("utf-8")), "text/csv")},
        )
        assert response.status_code == 200, response.text
        other_batch = response.json()["data"]

        owner_kpis = client.get("/restaurant/kpis", headers=owner_headers).json()["data"]
        other_kpis = client.get("/restaurant/kpis", headers=other_headers).json()["data"]
        assert owner_kpis["total_revenue"] == 1010.0
        assert other_kpis["total_revenue"] == 1010.0

        owner_rows = client.get("/restaurant/transactions", headers=owner_headers).json()["data"]
        other_rows = client.get("/restaurant/transactions", headers=other_headers).json()["data"]
        assert "OtherUserItem" not in {row["item"] for row in owner_rows["items"]}
        assert "OtherUserItem" in {row["item"] for row in other_rows["items"]}

        owner_imports = client.get("/restaurant/imports", headers=owner_headers).json()["data"]
        other_imports = client.get("/restaurant/imports", headers=other_headers).json()["data"]
        assert [item["id"] for item in owner_imports] == [owner_batch["id"]]
        assert [item["id"] for item in other_imports] == [other_batch["id"]]
        assert load_private_object(other_imports[0]["source_path"]) == other_file.encode("utf-8")

        owner_report = client.get(f"/restaurant/imports/{owner_batch['id']}/report", headers=owner_headers)
        assert owner_report.status_code == 200
        assert client.get(
            f"/restaurant/imports/{owner_batch['id']}/report", headers=other_headers
        ).status_code == 404

        forced = client.post(
            "/restaurant/imports/upload?force=true",
            headers=other_headers,
            files={"file": ("other.csv", io.BytesIO(other_file.encode("utf-8")), "text/csv")},
        )
        assert forced.status_code == 200
        assert client.get("/restaurant/kpis", headers=owner_headers).json()["data"]["total_transactions"] == 4
