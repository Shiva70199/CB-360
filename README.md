# CB 360 – Business Intelligence & Analytics Platform

**Tagline:** See Your Business from Every Angle.

**Workspace:** California Burrito Analytics — Restaurant Operations & Business Intelligence

CB 360 turns restaurant transactions into actionable business intelligence. It analyzes sales, menu performance, outlet operations and payment mix through one analytics platform. This build is the California Burrito Software Developer Intern technical assessment and uses the transaction dataset supplied by the company. It is an assessment project, not official California Burrito internal software.

Authenticated users import POS transaction line items (Excel/CSV), then explore revenue, menu items, outlets, order types and settlements through server-side aggregations. The product keeps the earlier CSV upload and charting tools alongside the restaurant workspace.

**Repository:** https://github.com/Shiva70199/CB-360  
**Branch:** `main`

## Features

- JWT authentication (register / login / protected routes)
- Restaurant ETL for Excel (`.xlsx`) and CSV with validation, rejection reports and idempotent re-imports
- KPI overview: revenue, orders, AOV, items sold, transaction count, active outlets
- Sales, product, outlet, order-type and payment analytics with ECharts
- Global filters (date, brand, outlet, category, order type, settlement)
- Data management: upload, default-path import, import history, paginated transactions, CSV export
- Dark / light theme
- Legacy CSV upload + charting retained at `/datasets` and `/analytics`

## Technology stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 14, React 18, Tailwind CSS, Apache ECharts, Plus Jakarta Sans |
| Backend | FastAPI, Pandas, openpyxl, SQLAlchemy, JWT, bcrypt |
| Database | SQLite (indexed fact table) |

## Architecture

```
CB 360/
├── app/                      # Next.js App Router
│   ├── dashboard/            # Overview KPIs + insights
│   ├── sales/ products/ outlets/ orders/ payments/
│   ├── data/                 # Import / export / transactions
│   ├── datasets/ analytics/  # Legacy CSV tools
│   └── login/ register/
├── components/bi/            # BI shell, filters, charts, KPI cards
├── lib/                      # API clients, auth, filters, theme
├── data/source/              # Place restaurant_transactions.xlsx here
├── data/reports/             # ETL import reports (generated)
├── backend/
│   ├── app/
│   │   ├── etl.py            # Excel/CSV ingest + validation
│   │   ├── restaurant_analytics.py  # SQL aggregations
│   │   ├── models.py         # User, Dataset, ImportBatch, TransactionLine
│   │   └── routers/restaurant.py
│   └── tests/
└── scripts/create_test_fixture.py
```

```
Excel/CSV → ETL (validate, normalize, order_key) → SQLite transaction_lines
                                                      ↓
                              FastAPI /restaurant/* aggregations
                                                      ↓
                              Next.js BI dashboard (filtered charts)
```

## Database structure

| Table | Role |
|-------|------|
| `users` | Registered accounts and password hashes |
| `datasets` | Legacy per-user CSV uploads |
| `import_batches` | Restaurant file imports, hash, row counts and status |
| `transaction_lines` | Valid POS line items used by every restaurant KPI |

Indexed columns on `transaction_lines` include bill number, order datetime, outlet, brand, menu group, order type, settlement and `order_key`.

## Database decision

**SQLite is retained.** ~300k indexed line items are well within SQLite’s comfort zone for server-side `SUM` / `COUNT(DISTINCT)` queries. Migrating to PostgreSQL would add deployment complexity without a clear local-assessment benefit. The schema remains portable (`DATABASE_URL`) if Postgres is needed later.

## ETL explanation

1. Read `.xlsx` (openpyxl) or `.csv`
2. Map headers via aliases (`Group` → `menu_group`, etc.)
3. Parse `Order_Datetime` with primary format `DD-MM-YYYY HH:MM:SS`
4. Coerce `Price` / `Quantity`; reject invalid rows with reasons
5. Compute `line_revenue = Price × Quantity`
6. Build composite **order_key** = `{BillNo}|{Outlet_Name}|{YYYY-MM-DD}`  
   BillNo alone is unsafe across outlets/days, so Total Orders = `COUNT(DISTINCT order_key)`
7. Bulk insert in chunks of 5,000
8. Idempotent by SHA-256 file hash (successful hash is reused)
9. Write JSON report under `data/reports/`

## KPI calculation methodology

| KPI | Definition |
|-----|------------|
| Total Revenue | `SUM(line_revenue)` |
| Total Orders | `COUNT(DISTINCT order_key)` |
| Average Order Value | Total Revenue / Total Orders |
| Total Items Sold | `SUM(quantity)` |
| Transaction Records | Count of valid line items |
| Active Outlets | `COUNT(DISTINCT outlet_name)` |

Period-over-period growth is returned **only** when both `date_from` and `date_to` are set. No invented growth figures.

## Performance considerations

- Aggregations run in SQL — the browser never receives 300k raw rows
- Transaction tables are paginated
- Indexes on bill_no, order_datetime, outlet_name, brand, menu_group, order_type, settlement, order_key
- Chart payloads are pre-aggregated series
- CSV export capped at 50,000 rows
- API responses include `meta.query_ms`

## Local setup

### Prerequisites

- Node.js 18+
- Python 3.12+ (or use the project embeddable runtime under `backend/.pyembed` if present)

### 1. Place the dataset

Copy the assessment workbook to:

```text
data/source/restaurant_transactions.xlsx
```

Do not commit the raw assessment file without permission.

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 — register, open **Data Management**, then **Import default path** or upload the Excel file.

### Environment variables

**Backend (`backend/.env`)**

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./databoard.db` | SQLAlchemy URL |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origins |
| `UPLOAD_DIR` | `./uploads` | Legacy CSV uploads |
| `RESTAURANT_SOURCE_PATH` | `../data/source/restaurant_transactions.xlsx` | Default import path |
| `REPORTS_DIR` | `../data/reports` | ETL reports |

**Frontend (`.env.local`)**

| Variable | Example |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

## Testing

```bash
cd backend
.venv\Scripts\activate
pytest -v
```

Critical coverage includes:

- Shared `BillNo` line items counting as one order (composite `order_key`)
- Revenue = price × quantity
- Missing/invalid row rejection
- Idempotent imports by file hash
- KPI/filter/pagination/export API behaviour
- Empty KPIs return zeros (not hardcoded demo metrics)

## Deployment

Two Vercel projects share this repository.

| Project | Root | Framework |
|---------|------|-----------|
| `cb-360-two` | repository root | Next.js |
| `cb-360-api` | `backend` | FastAPI, entry `index.py` |

Frontend: https://cb-360-two.vercel.app

The backend is not treated as deployed until `https://<api>/health/ready` returns database `ok`. There is no Neon connection string in this repository.

**Backend environment**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Neon **pooled** URL. `postgres://` and `postgresql://` are both accepted. Missing in production is an error, not SQLite. |
| `DATABASE_URL_UNPOOLED` | Neon **direct** URL for schema init and the one-time import. |
| `JWT_SECRET` | Random secret, at least 32 characters. The development default is rejected in production. |
| `CORS_ORIGINS` | `https://cb-360-two.vercel.app` plus any preview origins. Localhost is always allowed. |
| `UPLOAD_DIR` | Optional. Use `/tmp/uploads` only for request-scoped files. It is not permanent. |
| `REPORTS_DIR` | Optional. Use `/tmp/reports` for import reports. They are not permanent. |
| `STORAGE_BACKEND` | `local` in development. `s3` in production if dataset uploads must persist. |
| `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_REGION` | S3-compatible dataset storage. Restaurant analytics do not need these. |

**Frontend environment**

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend origin, no trailing slash. Local: `http://localhost:8000`. Production: the `cb-360-api` URL. |

Accounts that exist only in the local SQLite file are not copied to Neon. Register again after the Postgres schema is created.

Schema init does not drop tables. This project has no Alembic migrations, so `create_all` adds missing tables and does not change columns that already exist.

```bash
cd backend
# direct Neon URL in the environment; do not commit it
python scripts/init_db.py
python scripts/import_restaurant.py
```

`import_restaurant.py` reads `data/source/restaurant_transactions.xlsx`. That workbook is gitignored. If it is not on disk, the script stops and nothing is imported. Repeating the import reuses a successful file hash and does not insert the same line items again.

Health: `GET /health` and `GET /health/live` mean the process is up. `GET /health/ready` runs `SELECT 1` and does not return connection strings or stack traces.

## Trade-offs and assumptions

- Composite `order_key` is used without waiting for a full 300k uniqueness audit of the missing workbook; once the Excel file is available, re-check BillNo collisions across outlets/dates.
- SQLite chosen for simplicity and assessment fit; Postgres is optional via `DATABASE_URL`.
- Legacy CSV analytics remain available alongside California Burrito Analytics.
- Raw assessment dataset is gitignored.

## Phase status

| Phase | Status |
|-------|--------|
| 1 Repository & Excel audit | Done (Excel file not present locally — place under `data/source/`) |
| 2 Architecture plan | Done |
| 3 ETL pipeline | Done |
| 4 DB + indexes | Done (SQLite) |
| 5 Analytics APIs | Done |
| 6 Dashboard UI | Done |
| 7 Tests | Done (38 passed) |
| 8 Performance | Done (SQL aggregations, indexes, pagination) |
| 9 README / deploy prep | Done (deploy pending real hosting + dataset) |
