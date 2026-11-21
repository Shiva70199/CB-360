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

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
