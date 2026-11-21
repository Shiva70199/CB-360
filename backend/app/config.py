import os
from pathlib import Path

from pydantic_settings import BaseSettings

# backend/app/config.py -> project root is two levels up from this file's parent (backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

_INSECURE_JWT_SECRETS = {
    "change-me-in-production",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "sqlite:///./databoard.db"
    database_url_unpooled: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    upload_dir: str = "./uploads"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,https://cb-360-two.vercel.app"
    )
    # Resolved relative to project root when a relative path is given
    restaurant_source_path: str = str(_PROJECT_ROOT / "data" / "source" / "restaurant_transactions.xlsx")
    reports_dir: str = str(_PROJECT_ROOT / "data" / "reports")
    project_root: str = str(_PROJECT_ROOT)
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def is_production(self) -> bool:
        if os.getenv("VERCEL", "").strip() == "1":
            return True
        if os.getenv("VERCEL_ENV", "").strip().lower() == "production":
            return True
        return (self.environment or "").strip().lower() in {"production", "prod"}

    def jwt_secret_is_safe(self) -> bool:
        secret = (self.jwt_secret or "").strip()
        return secret not in _INSECURE_JWT_SECRETS and len(secret) >= 32

    def object_storage_configured(self) -> bool:
        return (
            self.storage_backend.strip().lower() == "s3"
            and bool(self.s3_bucket.strip())
            and bool(self.s3_access_key_id.strip())
            and bool(self.s3_secret_access_key.strip())
        )

    def resolve_restaurant_source_path(self) -> Path:
        path = Path(self.restaurant_source_path)
        if not path.is_absolute():
            path = Path(self.project_root) / path
        return path.resolve()

    def resolve_reports_dir(self) -> Path:
        # Vercel can only write under /tmp, and those files disappear after the request.
        if self.is_production() and not os.getenv("REPORTS_DIR", "").strip():
            path = Path("/tmp/reports")
        else:
            path = Path(self.reports_dir)
            if not path.is_absolute():
                path = Path(self.project_root) / path
        return path.resolve()

    def resolve_upload_dir(self) -> Path:
        if self.is_production() and not os.getenv("UPLOAD_DIR", "").strip():
            return Path("/tmp/uploads")
        path = Path(self.upload_dir)
        if not path.is_absolute():
            # `./uploads` stays inside backend/, matching local uvicorn's working directory.
            path = _BACKEND_DIR / path
        return path


settings = Settings()
