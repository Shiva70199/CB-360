from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DatasetOut(BaseModel):
    id: int
    name: str
    row_count: int
    column_count: int
    columns: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: list[DatasetOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    is_numeric: bool


class ComputeRequest(BaseModel):
    dataset_id: int
    column: str


class ComputeResponse(BaseModel):
    column: str
    min: float | None
    max: float | None
    sum: float | None
    count: int


class ChartDataRequest(BaseModel):
    x_column: str
    y_column: str


class ChartDataResponse(BaseModel):
    x: list[Any]
    y: list[float | None]


class DashboardStats(BaseModel):
    total_datasets: int
    total_rows: int
    latest_upload: DatasetOut | None
    available_charts: list[str]


# --- Restaurant analytics ---


class ImportFromPathRequest(BaseModel):
    path: str | None = None
    force: bool = False


class RestaurantApiMeta(BaseModel):
    query_ms: float | None = None


class RestaurantApiResponse(BaseModel):
    data: Any
    meta: RestaurantApiMeta | None = None


class KpiComparisonGrowth(BaseModel):
    total_revenue_pct: float | None = None
    total_orders_pct: float | None = None
    aov_pct: float | None = None


class KpiPrevious(BaseModel):
    total_revenue: float
    total_orders: int
    aov: float
    total_items_sold: float
    total_transactions: int
    active_outlets: int


class KpiComparison(BaseModel):
    previous: KpiPrevious
    growth: KpiComparisonGrowth


class KpiData(BaseModel):
    total_revenue: float = 0.0
    total_orders: int = 0
    aov: float = 0.0
    total_items_sold: float = 0.0
    total_transactions: int = 0
    active_outlets: int = 0
    comparison: KpiComparison | None = None


class TrendPoint(BaseModel):
    period: str | None
    revenue: float
    orders: int


class NamedRevenueRow(BaseModel):
    name: str | None
    revenue: float
    orders: int
    aov: float = 0.0
    items_sold: float = 0.0


class ProductRow(BaseModel):
    item: str | None
    menu_group: str | None
    revenue: float
    quantity: float
    avg_price: float | None = None
    contribution_pct: float | None = None


class PaginatedProducts(BaseModel):
    items: list[ProductRow]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionRow(BaseModel):
    id: int
    bill_no: str
    outlet_name: str
    brand: str
    order_datetime: str | None
    menu_group: str
    item: str
    price: float
    quantity: float
    line_revenue: float
    order_type: str
    settlement: str
    order_key: str


class PaginatedTransactions(BaseModel):
    items: list[TransactionRow]
    total: int
    page: int
    page_size: int
    total_pages: int


class FilterOptions(BaseModel):
    brands: list[str]
    outlets: list[str]
    menu_groups: list[str]
    order_types: list[str]
    settlements: list[str]
    date_min: str | None = None
    date_max: str | None = None


class ImportBatchOut(BaseModel):
    id: int
    filename: str
    file_hash: str
    imported_at: str | None
    status: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    missing_values: dict[str, Any] = Field(default_factory=dict)
    error_report_path: str | None = None
    source_path: str | None = None
    notes: str | None = None


class InsightItem(BaseModel):
    title: str
    detail: str


class OrderTypeOutletRow(BaseModel):
    outlet: str | None
    order_type: str | None
    revenue: float
    orders: int


class OrderTypeAnalytics(BaseModel):
    distribution: list[NamedRevenueRow]
    outlet_wise: list[OrderTypeOutletRow]
