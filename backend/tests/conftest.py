import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from poltracker.models import Base

FIXTURES = Path(__file__).parent / "fixtures"

# Point the whole suite at PostgreSQL by exporting this variable. The database name must contain
# "test" because the fixtures DROP and recreate every table. See docs/PRODUCTION_READINESS.md.
PG_ENV = "POLTRACKER_TEST_DATABASE_URL"


def pg_test_url() -> str | None:
    url = os.environ.get(PG_ENV)
    if not url:
        return None
    from poltracker.config import normalize_database_url

    url = normalize_database_url(url)
    name = make_url(url).database or ""
    if "test" not in name:
        raise RuntimeError(
            f"{PG_ENV} points at database {name!r}. Refusing to drop tables: the database name must contain 'test'."
        )
    return url


def _sqlite_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def _pg_factory(url: str):
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def recent_body() -> dict:
    return json.loads((FIXTURES / "congressinvests_recent.json").read_text())


@pytest.fixture
def session_factory():
    """SQLite in memory by default, or PostgreSQL when POLTRACKER_TEST_DATABASE_URL is set."""
    url = pg_test_url()
    engine, factory = _pg_factory(url) if url else _sqlite_factory()
    yield factory
    engine.dispose()


@pytest.fixture
def sqlite_session_factory():
    engine, factory = _sqlite_factory()
    yield factory
    engine.dispose()


@pytest.fixture
def pg_session_factory():
    url = pg_test_url()
    if not url:
        pytest.skip(f"set {PG_ENV} to run PostgreSQL tests")
    engine, factory = _pg_factory(url)
    yield factory
    engine.dispose()
