import pytest
from pydantic import ValidationError

from poltracker.config import Settings, normalize_database_url
from poltracker.db import make_engine


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgres://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),  # already has a driver
        ("sqlite:///./poltracker.db", "sqlite:///./poltracker.db"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_database_url_normalization(raw, expected):
    assert normalize_database_url(raw) == expected


def test_default_is_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Settings(_env_file=None).database_url == "sqlite:///./poltracker.db"


def test_settings_normalize_a_production_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:secret@example.test/db?sslmode=require")
    assert Settings(_env_file=None).database_url.startswith("postgresql+psycopg://")


def test_postgres_engine_is_built_for_a_suspending_database():
    engine = make_engine("postgresql://user:pw@example.test/db")  # lazy: no connection is attempted
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True
    assert engine.pool.size() == 3


def test_sqlite_engine_keeps_foreign_keys_on(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'x.db'}")
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


# ── CORS configuration ───────────────────────────────────────────────────────


def test_cors_defaults_are_local_only():
    origins = Settings(_env_file=None).cors_origin_list
    assert origins and all("localhost" in o or "127.0.0.1" in o for o in origins)


def test_cors_origins_are_parsed_and_tidied():
    s = Settings(_env_file=None, cors_origins=" https://a.example/ , https://b.example,,https://a.example ")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]


def test_empty_cors_disables_cross_origin():
    assert Settings(_env_file=None, cors_origins="").cors_origin_list == []


@pytest.mark.parametrize("bad", ["example.com", "https://example.com/app", "ftp://example.com", "https://a.example, nope"])
def test_malformed_cors_origin_fails_fast(bad):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=bad)


def test_cors_wildcard_must_be_explicit():
    assert Settings(_env_file=None, cors_origins="*").cors_origin_list == ["*"]
