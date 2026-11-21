"""
Generate a tiny restaurant transactions fixture for automated tests only.

Writes:
  backend/tests/fixtures/restaurant_sample.csv
  backend/tests/fixtures/restaurant_sample.xlsx

Does NOT write into data/source (production ingest path).
"""

from __future__ import annotations

import csv
from pathlib import Path

ROWS = [
    # Two line items, same BillNo + outlet + date → 1 order
    {
        "BillNo": "B100",
        "Outlet_Name": "Downtown",
        "Brand": "CafeOne",
        "Order_Datetime": "15-01-2024 12:30:00",
        "Group": "Beverages",
        "Item": "Latte",
        "Price": "120",
        "Quantity": "2",
        "Order_Type": "Dine-In",
        "Settlement": "Card",
    },
    {
        "BillNo": "B100",
        "Outlet_Name": "Downtown",
        "Brand": "CafeOne",
        "Order_Datetime": "15-01-2024 12:30:00",
        "Group": "Food",
        "Item": "Sandwich",
        "Price": "180",
        "Quantity": "1",
        "Order_Type": "Dine-In",
        "Settlement": "Card",
    },
    # Same BillNo, different outlet → separate order (collision case)
    {
        "BillNo": "B100",
        "Outlet_Name": "Airport",
        "Brand": "CafeOne",
        "Order_Datetime": "15-01-2024 18:00:00",
        "Group": "Beverages",
        "Item": "Espresso",
        "Price": "90",
        "Quantity": "1",
        "Order_Type": "Takeaway",
        "Settlement": "Cash",
    },
    # Another order
    {
        "BillNo": "B200",
        "Outlet_Name": "Downtown",
        "Brand": "BiteBrand",
        "Order_Datetime": "16-01-2024 09:15:00",
        "Group": "Food",
        "Item": "Burger",
        "Price": "250",
        "Quantity": "2",
        "Order_Type": "Delivery",
        "Settlement": "UPI",
    },
    # Invalid row (missing price) — should be rejected by ETL
    {
        "BillNo": "B300",
        "Outlet_Name": "Downtown",
        "Brand": "CafeOne",
        "Order_Datetime": "16-01-2024 10:00:00",
        "Group": "Food",
        "Item": "Fries",
        "Price": "",
        "Quantity": "1",
        "Order_Type": "Dine-In",
        "Settlement": "Cash",
    },
]

COLUMNS = [
    "BillNo",
    "Outlet_Name",
    "Brand",
    "Order_Datetime",
    "Group",
    "Item",
    "Price",
    "Quantity",
    "Order_Type",
    "Settlement",
]


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "backend" / "tests" / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "restaurant_sample.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ROWS)

    xlsx_path = out_dir / "restaurant_sample.xlsx"
    try:
        import pandas as pd

        pd.DataFrame(ROWS).to_excel(xlsx_path, index=False, engine="openpyxl")
        print(f"Wrote {xlsx_path}")
    except Exception as exc:
        print(f"CSV written; XLSX skipped ({exc})")

    print(f"Wrote {csv_path}")
    # Expected valid revenue: (120*2)+(180*1)+(90*1)+(250*2) = 240+180+90+500 = 1010
    # Expected orders: 3 (B100|Downtown|2024-01-15, B100|Airport|2024-01-15, B200|Downtown|2024-01-16)
    print("Expected: valid_rows=4, rejected=1, revenue=1010, orders=3")


if __name__ == "__main__":
    main()
