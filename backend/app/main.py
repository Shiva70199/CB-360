import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import Dataset, ImportBatch, TransactionLine, User  # noqa: F401 — register metadata
from app.routers import analytics, auth, dashboard, datasets, restaurant
from app.services import ensure_upload_dir

# Ensure new restaurant tables (import_batches, transaction_lines) are created
Base.metadata.create_all(bind=engine)
ensure_upload_dir()
os.makedirs(settings.resolve_reports_dir(), exist_ok=True)

app = FastAPI(title="CB 360 API", version="1.1.0")

# Browsers treat localhost and 127.0.0.1 as different origins. A preflight
# from the other host was rejected with 400, so register/login never ran.
_LOCAL_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
origins: list[str] = []
for origin in (*_LOCAL_ORIGINS, *(o.strip() for o in settings.cors_origins.split(","))):
    if origin and origin not in origins:
        origins.append(origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(restaurant.router)


@app.get("/health")
def health():
    return {"status": "ok"}
