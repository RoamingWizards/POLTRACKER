"""Run the real Alembic migrations on a clean PostgreSQL database.

Skipped unless POLTRACKER_TEST_DATABASE_URL is set. This test WIPES the public schema of that database,
so the name must contain "test" (enforced by conftest).
"""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from conftest import pg_test_url
from sqlalchemy.orm import sessionmaker
from test_migration_0003 import load_migration, seed_legacy

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
TABLES = {"alembic_version", "committee_assignments", "ingest_state", "politician_alias_overrides", "politician_llm_suggestions", "politicians", "price_bars", "securities", "trades"}


@pytest.fixture
def clean_pg(monkeypatch):
    url = pg_test_url()
    if not url:
        pytest.skip("set POLTRACKER_TEST_DATABASE_URL to run PostgreSQL migration tests")
    engine = sa.create_engine(url)
    with engine.begin() as c:
        c.execute(sa.text("drop schema public cascade"))
        c.execute(sa.text("create schema public"))
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield engine, cfg
    get_settings.cache_clear()
    engine.dispose()


def version(engine):
    with engine.connect() as c:
        return c.execute(sa.text("select version_num from alembic_version")).scalar()


def test_all_migrations_apply_to_a_clean_database(clean_pg):
    engine, cfg = clean_pg
    command.upgrade(cfg, "head")
    assert version(engine) == "0009"
    assert set(sa.inspect(engine).get_table_names()) == TABLES
    assert "last_success_at" in [c["name"] for c in sa.inspect(engine).get_columns("ingest_state")]


def test_each_revision_applies_in_order(clean_pg):
    engine, cfg = clean_pg
    for rev in ("0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009"):
        command.upgrade(cfg, rev)
        assert version(engine) == rev


def test_0005_downgrades_and_upgrades_again(clean_pg):
    engine, cfg = clean_pg
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0004")
    assert "last_success_at" not in [c["name"] for c in sa.inspect(engine).get_columns("ingest_state")]
    command.upgrade(cfg, "head")
    assert version(engine) == "0009"


def test_0003_data_migration_works_on_postgresql(clean_pg):
    """The merge and fingerprint rewrite use raw SQL; prove it on PostgreSQL with legacy-shaped data."""
    engine, cfg = clean_pg
    command.upgrade(cfg, "0002")
    mig = load_migration()
    seed_legacy(engine, mig)
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        names = {r[0] for r in c.execute(sa.text("select name from politicians"))}
        assert names == {"John McGuire", "Scott Franklin", "Gary C Peters", "Dan Crenshaw", "Daniel Crenshaw"}
        assert c.execute(sa.text("select count(*) from trades")).scalar() == 9
        assert c.execute(sa.text("select count(distinct fingerprint) from trades")).scalar() == 9
        assert c.execute(sa.text("select count(*) from trades where fingerprint like 'tmp-%'")).scalar() == 0
