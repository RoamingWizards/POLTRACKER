"""Migration 0009: seven new empty tables. Nothing existing is altered; reversible."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
NEW = {"legislation", "legislation_subjects", "legislation_committees", "politician_legislation", "bill_actions", "hearings", "hearing_committees"}
EXISTING = ["politicians", "trades", "securities", "price_bars", "committee_assignments", "ingest_state", "politician_alias_overrides", "politician_llm_suggestions"]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm9.db'}"
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
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, bioguide_id, created_at) values (7, 'house:a', 'Lloyd Doggett', 'house', 'D000399', '2026-01-01')")
        c.exec_driver_sql("insert into securities (id, ticker, created_at) values (3, 'XYZ', '2026-01-01')")
        c.exec_driver_sql("insert into trades (source, fingerprint, politician_id, security_id, politician_name, chamber, transaction_type, transaction_date, created_at) "
                          "values ('x', 'f1', 7, 3, 'Lloyd Doggett', 'house', 'buy', '2026-01-02', '2026-01-03')")
        c.exec_driver_sql("insert into price_bars (security_id, date, close, adj_close, provider) values (3, '2026-01-02', 1.0, 1.0, 't')")
        c.exec_driver_sql("insert into committee_assignments (politician_id, committee_name, committee_code, subcommittee_code, role, chamber, source, fetched_at) "
                          "values (7, 'Committee on Ways and Means', 'WM00', '', 'Member', 'house', 'house.clerk', '2026-01-01')")


def test_upgrade_adds_only_new_empty_tables_and_changes_no_existing_data(db):
    engine, cfg = db
    command.upgrade(cfg, "0008")
    seed(engine)
    before = snapshot(engine)
    assert not NEW & set(sa.inspect(engine).get_table_names())
    command.upgrade(cfg, "head")
    assert NEW <= set(sa.inspect(engine).get_table_names())
    assert snapshot(engine) == before  # politicians, trades, securities, price bars and committee assignments are untouched
    with engine.connect() as c:
        assert all(c.exec_driver_sql(f"select count(*) from {t}").scalar() == 0 for t in NEW)
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0009"


def test_the_unique_keys_prevent_duplicates_at_the_database_level(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    with engine.begin() as c:
        c.exec_driver_sql("insert into legislation (id, congress, bill_type, bill_number, updated_at) values (1, 119, 'hr', 5, '2026-01-01')")
        c.exec_driver_sql("insert into legislation_subjects (legislation_id, subject) values (1, 'Health')")
        c.exec_driver_sql("insert into legislation_committees (legislation_id, committee_code, committee_name) values (1, 'hsif00', 'E&C')")
        c.exec_driver_sql("insert into politician_legislation (politician_id, legislation_id, relationship) values (7, 1, 'sponsor')")
        c.exec_driver_sql("insert into bill_actions (legislation_id, action_date, action_text, action_key) values (1, '2026-01-01', 't', 'k1')")
        c.exec_driver_sql("insert into hearings (id, congress, chamber, jacket_number, updated_at) values (1, 119, 'house', 9, '2026-01-01')")
        c.exec_driver_sql("insert into hearing_committees (hearing_id, committee_code, committee_name) values (1, 'hsag00', 'Ag')")
    duplicates = [
        "insert into legislation (congress, bill_type, bill_number, updated_at) values (119, 'hr', 5, '2026-01-02')",
        "insert into legislation_subjects (legislation_id, subject) values (1, 'Health')",
        "insert into legislation_committees (legislation_id, committee_code, committee_name) values (1, 'hsif00', 'other name')",
        "insert into politician_legislation (politician_id, legislation_id, relationship) values (7, 1, 'sponsor')",
        "insert into bill_actions (legislation_id, action_date, action_text, action_key) values (1, '2026-02-02', 'other', 'k1')",
        "insert into hearings (congress, chamber, jacket_number, updated_at) values (119, 'house', 9, '2026-01-02')",
        "insert into hearing_committees (hearing_id, committee_code, committee_name) values (1, 'hsag00', 'x')",
    ]
    for sql in duplicates:
        with pytest.raises(sa.exc.IntegrityError), engine.begin() as c:
            c.exec_driver_sql(sql)
    with engine.begin() as c:  # a different relationship for the same politician and bill is allowed (sponsor and cosponsor)
        c.exec_driver_sql("insert into politician_legislation (politician_id, legislation_id, relationship) values (7, 1, 'cosponsor')")


def test_downgrade_removes_only_the_new_tables(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed(engine)
    before = snapshot(engine)
    command.downgrade(cfg, "0008")
    assert not NEW & set(sa.inspect(engine).get_table_names()) and snapshot(engine) == before
    command.upgrade(cfg, "head")  # and it can go forward again


def test_the_models_match_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    insp = sa.inspect(engine)
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in insp.get_columns(table.name)}, table.name
        assert {tuple(u["column_names"]) for u in insp.get_unique_constraints(table.name)} >= {
            tuple(c.name for c in u.columns) for u in table.constraints if isinstance(u, sa.UniqueConstraint) and len(u.columns)}, table.name
