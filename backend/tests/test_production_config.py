import os

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateTable

from app.auth import hash_password, verify_password
from app.database import _build_engine, normalize_database_url
from app.main import app
from app.models import User


def test_normalize_postgres_schemes():
    pooled = normalize_database_url("postgres://user:secret@ep-pooler.neon.tech/neondb")
    direct = normalize_database_url("postgresql://user:secret@ep.neon.tech/neondb?sslmode=require")
    assert pooled.startswith("postgresql+psycopg://")
    assert direct.startswith("postgresql+psycopg://")
    assert "postgresql+psycopg://user:secret@" in pooled
    assert normalize_database_url("sqlite:///./databoard.db") == "sqlite:///./databoard.db"
    assert normalize_database_url("postgresql+psycopg://user@host/db") == "postgresql+psycopg://user@host/db"


def test_health_live_does_not_require_postgres():
    client = TestClient(app)
    live = client.get("/health/live")
    health = client.get("/health")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_health_ready_uses_local_sqlite():
    client = TestClient(app)
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["database"] == "ok"
    assert body["auth"] == "ok"


def test_production_frontend_origin_is_allowed():
    client = TestClient(app)
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://cb-360-two.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://cb-360-two.vercel.app"


def test_local_origin_is_still_allowed():
    client = TestClient(app)
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_production_without_database_url_does_not_use_sqlite(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Re-import would cache settings. Call the helper that reads the environment directly.
    from app.database import production_database_url

    assert production_database_url() is None
    assert os.getenv("VERCEL") == "1"


def test_user_model_matches_postgres_users_table():
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert User.__tablename__ == "users"
    for column in ("id", "email", "hashed_password", "created_at"):
        assert column in ddl


def test_postgres_engine_disables_prepared_statements_and_pooling():
    engine = _build_engine("postgresql+psycopg://user:secret@localhost/neondb")
    assert isinstance(engine.pool, NullPool)
    captured = {}

    def fake_connect(*args, **kwargs):
        captured["kwargs"] = kwargs
        raise RuntimeError("do not connect")

    engine.dialect.connect = fake_connect
    try:
        engine.connect()
    except RuntimeError:
        pass
    assert captured["kwargs"]["prepare_threshold"] is None
    engine.dispose()


def test_password_verification_accepts_its_own_hash_and_rejects_bad_hashes():
    hashed = hash_password("pass1234")
    assert hashed.startswith("$2")
    assert verify_password("pass1234", hashed) is True
    assert verify_password("wrong-password", hashed) is False
    assert verify_password("pass1234", "not-a-bcrypt-hash") is False
