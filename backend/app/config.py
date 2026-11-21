from pathlib import Path

from pydantic_settings import BaseSettings

# backend/app/config.py -> project root is two levels up from this file's parent (backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "sqlite:///./databoard.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:3000"
    # Resolved relative to project root when a relative path is given
    restaurant_source_path: str = str(_PROJECT_ROOT / "data" / "source" / "restaurant_transactions.xlsx")
    reports_dir: str = str(_PROJECT_ROOT / "data" / "reports")
    project_root: str = str(_PROJECT_ROOT)

    class Config:
        env_file = ".env"

    def resolve_restaurant_source_path(self) -> Path:
        path = Path(self.restaurant_source_path)
        if not path.is_absolute():
            path = Path(self.project_root) / path
        return path.resolve()

    def resolve_reports_dir(self) -> Path:
        path = Path(self.reports_dir)
        if not path.is_absolute():
            path = Path(self.project_root) / path
        return path.resolve()


settings = Settings()
