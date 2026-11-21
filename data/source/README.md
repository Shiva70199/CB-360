# Restaurant source data

Place the assessment workbook here:

```text
data/source/restaurant_transactions.xlsx
```

Expected columns:

- BillNo
- Outlet_Name
- Brand
- Order_Datetime (`DD-MM-YYYY HH:MM:SS`)
- Group
- Item
- Price
- Quantity
- Order_Type
- Settlement

Then sign in to CB 360 → **Data Management** → **Import default path**.

Raw `.xlsx` / `.csv` files in this folder are gitignored and should not be committed without permission.
