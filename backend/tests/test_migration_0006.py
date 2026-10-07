"""Migration 0006 only adds nullable politician columns and a committee table. Existing rows and ids survive."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
NEW = {"bioguide_id", "district", "official_url", "active", "term_start_year", "term_end_year", "enriched_at",
       "enrichment_source", "enrichment_status", "enrichment_note", "enrichment_checked_at"}


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm6.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("politicians")}


def seed(engine):
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, party, state, created_at) values "
                          "(7, 'house:lloyddoggett', 'Lloyd Doggett', 'house', 'D', 'TX', '2026-01-01'), "
                          "(9, 'senate:ronwyden', 'Ron Wyden', 'senate', null, null, '2026-01-01')")
        c.exec_driver_sql("insert into trades (source, fingerprint, politician_id, politician_name, chamber, transaction_type, "
                          "transaction_date, created_at) values ('x', 'f1', 7, 'Lloyd Doggett', 'house', 'buy', '2026-01-02', '2026-01-03')")


def test_upgrade_preserves_politicians_ids_and_trades_and_leaves_new_fields_empty(db):
    engine, cfg = db
    command.upgrade(cfg, "0005")
    assert not NEW & cols(engine)
    seed(engine)
    command.upgrade(cfg, "head")
    assert NEW <= cols(engine) and "committee_assignments" in sa.inspect(engine).get_table_names()
    with engine.connect() as c:
        rows = c.exec_driver_sql("select id, name, party, state, bioguide_id, enrichment_status, active from politicians order by id").all()
        assert [tuple(r) for r in rows] == [(7, "Lloyd Doggett", "D", "TX", None, None, None), (9, "Ron Wyden", None, None, None, None, None)]
        assert c.exec_driver_sql("select politician_id from trades").scalar() == 7
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0011"


def test_a_bioguide_id_can_belong_to_only_one_politician(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    with engine.begin() as c:
        c.exec_driver_sql("update politicians set bioguide_id = 'D000399' where id = 7")
        c.exec_driver_sql("update politicians set bioguide_id = null where id = 9")  # several NULLs are fine
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as c:
        c.exec_driver_sql("update politicians set bioguide_id = 'D000399' where id = 9")


def test_downgrade_removes_only_the_new_columns_and_table(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    command.downgrade(cfg, "0005")
    assert not NEW & cols(engine) and "committee_assignments" not in sa.inspect(engine).get_table_names()
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 2
        assert c.exec_driver_sql("select count(*) from trades").scalar() == 1
    command.upgrade(cfg, "head")  # and it can go forward again


def test_the_model_matches_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name
