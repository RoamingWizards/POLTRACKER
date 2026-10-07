"""Migration 0010 adds the committee/industry mapping table. Nothing existing changes; reversible."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
EXISTING = ["politicians", "trades", "securities", "price_bars", "committee_assignments", "politician_alias_overrides"]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm10.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def snapshot(engine):
    with engine.connect() as c:
        return {t: sorted(map(tuple, c.exec_driver_sql(f"select * from {t}").all())) for t in EXISTING}


def seed(engine):
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (7, 'house:a', 'A', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into securities (id, ticker, sic_code, industry, created_at) values (3, 'LMT', '3760', 'Guided Missiles', '2026-01-01')")
        c.exec_driver_sql("insert into committee_assignments (politician_id, committee_name, committee_code, subcommittee_code, role, chamber, source, fetched_at) "
                          "values (7, 'Committee on Armed Services', 'AS00', '', 'Member', 'house', 'house.clerk', '2026-01-01')")


def test_upgrade_adds_an_empty_table_and_changes_no_existing_data(db):
    engine, cfg = db
    command.upgrade(cfg, "0009")
    seed(engine)
    before = snapshot(engine)
    assert "committee_industry_mappings" not in sa.inspect(engine).get_table_names()
    command.upgrade(cfg, "head")
    assert "committee_industry_mappings" in sa.inspect(engine).get_table_names() and snapshot(engine) == before
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from committee_industry_mappings").scalar() == 0
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0010"


def test_downgrade_removes_only_the_new_table(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    before = snapshot(engine)
    command.downgrade(cfg, "0009")
    assert "committee_industry_mappings" not in sa.inspect(engine).get_table_names() and snapshot(engine) == before
    command.upgrade(cfg, "head")


def test_the_model_matches_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name
