from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    import_batches: Mapped[list["ImportBatch"]] = relationship(
        "ImportBatch", back_populates="user", cascade="all, delete-orphan"
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_dataset_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="datasets")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    missing_values_json: Mapped[str] = mapped_column(Text, default="{}")
    error_report_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="import_batches")
    lines: Mapped[list["TransactionLine"]] = relationship(
        "TransactionLine", back_populates="import_batch", cascade="all, delete-orphan"
    )


class TransactionLine(Base):
    """
    One row per line item on a restaurant bill.

    Order identity (order_key):
    BillNo alone is NOT safe as a unique order identifier. In multi-outlet
    chains the same BillNo can collide across outlets, and bill sequences often
    reset by day/register. Therefore:
        order_key = f"{bill_no}|{outlet_name}|{order_date}"
    where order_date is the calendar date of Order_Datetime (YYYY-MM-DD).
    Total Orders = COUNT(DISTINCT order_key).
    """

    __tablename__ = "transaction_lines"
    __table_args__ = (
        Index("ix_txn_bill_no", "bill_no"),
        Index("ix_txn_order_datetime", "order_datetime"),
        Index("ix_txn_outlet_name", "outlet_name"),
        Index("ix_txn_brand", "brand"),
        Index("ix_txn_menu_group", "menu_group"),
        Index("ix_txn_order_type", "order_type"),
        Index("ix_txn_settlement", "settlement"),
        Index("ix_txn_order_key", "order_key"),
        Index("ix_txn_import_batch_id", "import_batch_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bill_no: Mapped[str] = mapped_column(String(128), nullable=False)
    outlet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    order_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    menu_group: Mapped[str] = mapped_column(String(255), nullable=False)
    item: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    line_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    order_type: Mapped[str] = mapped_column(String(128), nullable=False)
    settlement: Mapped[str] = mapped_column(String(128), nullable=False)
    order_key: Mapped[str] = mapped_column(String(512), nullable=False)

    import_batch: Mapped["ImportBatch"] = relationship("ImportBatch", back_populates="lines")
