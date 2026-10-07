"""Migration 0009 adds nullable company-profile columns to securities. Nothing existing changes; reversible."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
NEW = {"company_name", "cik", "sic_code", "industry", "sector", "exchange", "profile_source", "profile_source_url", "profile_status", "profile_note",
       "profile_checked_at", "profile_updated_at"}


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm9.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("securities")}


def seed(engine):
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (7, 'house:a', 'A', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into securities (id, ticker, name, price_status, created_at) values (3, 'LMT', 'Lockheed as filed', 'ok', '2026-01-01'), (4, 'SPY', null, null, '2026-01-01')")
        c.exec_driver_sql("insert into trades (source, fingerprint, politician_id, security_id, politician_name, chamber, ticker, transaction_type, transaction_date, created_at) "
                          "values ('x', 'f1', 7, 3, 'A', 'house', 'LMT', 'buy', '2026-01-02', '2026-01-03')")


def test_upgrade_adds_empty_nullable_columns_and_preserves_every_row_and_relationship(db):
    engine, cfg = db
    command.upgrade(cfg, "0008")
    seed(engine)
    assert not NEW & cols(engine)
    with engine.connect() as c:
        before = [tuple(r) for r in c.exec_driver_sql("select id, ticker, name, price_status from securities order by id")]
        tbefore = [tuple(r) for r in c.exec_driver_sql("select * from trades")]
    command.upgrade(cfg, "head")
    assert NEW <= cols(engine)
    with engine.connect() as c:
        assert [tuple(r) for r in c.exec_driver_sql("select id, ticker, name, price_status from securities order by id")] == before
        assert [tuple(r) for r in c.exec_driver_sql("select * from trades")] == tbefore
        assert c.exec_driver_sql("select count(*) from securities where profile_status is not null or cik is not null or sector is not null").scalar() == 0
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0009"


def test_downgrade_removes_only_the_new_columns(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    with engine.begin() as c:
        c.exec_driver_sql("update securities set cik = '0000936468', industry = 'Aircraft' where id = 3")
    command.downgrade(cfg, "0008")
    assert not NEW & cols(engine)
    with engine.connect() as c:
        assert [tuple(r) for r in c.exec_driver_sql("select id, ticker, name from securities order by id")] == [(3, "LMT", "Lockheed as filed"), (4, "SPY", None)]
        assert c.exec_driver_sql("select count(*) from trades").scalar() == 1
    command.upgrade(cfg, "head")


def test_the_model_matches_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name
