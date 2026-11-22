import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, database_status, engine
from app.models import Dataset, ImportBatch, TransactionLine, User  # noqa: F401 — register metadata
from app.routers import analytics, auth, dashboard, datasets, restaurant

# Local SQLite still creates tables on startup. Production Postgres does not:
# run `python scripts/init_db.py` once against Neon instead of on every cold start.
if engine is not None and str(engine.url).startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="CB 360 API", version="1.1.0")
logger = logging.getLogger("cb360.api")


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response

# Browsers treat localhost and 127.0.0.1 as different origins.
_LOCAL_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
origins: list[str] = []
for origin in (*_LOCAL_ORIGINS, *(o.strip().rstrip("/") for o in settings.cors_origins.split(","))):
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


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Unhandled errors were turned into a plain-text 500 outside CORS, so the
    # browser reported that the API could not be reached.
    if isinstance(exc, HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    # Log only the type. Database exceptions can include the connection string.
    logger.error(
        "api_failure request_id=%s endpoint=%s failure_stage=unhandled exception_type=%s http_status=500",
        getattr(request.state, "request_id", "unknown"),
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse({"detail": "The API could not complete that request."}, status_code=500)


@app.get("/health")
@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    database_ok, database_state = database_status()
    auth_state = "ok" if (not settings.is_production() or settings.jwt_secret_is_safe()) else "not_configured"
    body = {"status": "ok", "database": database_state, "auth": auth_state}
    if database_ok and auth_state == "ok":
        return body
    body["status"] = "unavailable"
    return JSONResponse(body, status_code=503)
