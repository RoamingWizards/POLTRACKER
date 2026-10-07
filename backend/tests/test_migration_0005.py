"""Migration 0005 adds ingest_state.last_success_at. Additive and reversible."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm5.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield url, cfg
    get_settings.cache_clear()


def columns(url):
    return [c["name"] for c in sa.inspect(sa.create_engine(url)).get_columns("ingest_state")]


def test_upgrade_keeps_existing_rows_and_leaves_the_new_column_empty(db):
    url, cfg = db
    command.upgrade(cfg, "0004")
    assert "last_success_at" not in columns(url)
    engine = sa.create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql("insert into ingest_state (source, backfill_complete, updated_at) values ('congressinvests', 1, '2026-01-01 00:00:00')")
    command.upgrade(cfg, "head")
    assert "last_success_at" in columns(url)
    with engine.connect() as c:
        row = c.exec_driver_sql("select source, backfill_complete, last_success_at from ingest_state").one()
    assert tuple(row) == ("congressinvests", 1, None)


def test_downgrade_removes_only_the_new_column(db):
    url, cfg = db
    command.upgrade(cfg, "head")
    engine = sa.create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql("insert into ingest_state (source, backfill_complete, updated_at, last_success_at) values ('congressinvests', 1, '2026-01-01', '2026-01-02')")
    command.downgrade(cfg, "0004")
    assert "last_success_at" not in columns(url)
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from ingest_state").scalar() == 1


def test_head_is_0008_on_a_clean_database(db):
    url, cfg = db
    command.upgrade(cfg, "head")
    with sa.create_engine(url).connect() as c:
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0008"
