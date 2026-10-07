"""Migration 0008: one new empty table; existing data untouched; reversible."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm8.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def test_upgrade_preserves_data_and_adds_an_empty_cache_table_and_downgrade_removes_it(db):
    engine, cfg = db
    command.upgrade(cfg, "0007")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, bioguide_id, created_at) values (3, 'k', 'Lloyd Doggett', 'house', 'D000399', '2026-01-01')")
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        assert c.exec_driver_sql("select bioguide_id from politicians where id = 3").scalar() == "D000399"
        assert c.exec_driver_sql("select count(*) from politician_llm_suggestions").scalar() == 0
    command.downgrade(cfg, "0007")
    assert "politician_llm_suggestions" not in sa.inspect(engine).get_table_names()
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 1
