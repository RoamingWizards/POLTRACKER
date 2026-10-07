"""Migration 0007: one nullable column and one empty table. Existing data is untouched."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm7.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def test_upgrade_keeps_enriched_politicians_and_adds_an_empty_override_table(db):
    engine, cfg = db
    command.upgrade(cfg, "0006")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, bioguide_id, enrichment_status, created_at) "
                          "values (7, 'house:a', 'Lloyd Doggett', 'house', 'D000399', 'matched', '2026-01-01')")
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        assert tuple(c.exec_driver_sql("select id, name, bioguide_id, enrichment_status, enrichment_method from politicians").one()) == (
            7, "Lloyd Doggett", "D000399", "matched", None)
        assert c.exec_driver_sql("select count(*) from politician_alias_overrides").scalar() == 0


def test_an_override_row_is_unique_per_politician_and_per_bioguide_id(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    with engine.begin() as c:
        for i in (1, 2):
            c.exec_driver_sql(f"insert into politicians (id, canonical_key, name, chamber, created_at) values ({i}, 'k{i}', 'n{i}', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into politician_alias_overrides (politician_id, bioguide_id, reason, source, reviewed_at, created_at) "
                          "values (1, 'C001120', 'r', 's', '2026-01-01', '2026-01-01')")
    for sql in ("(1, 'X000001', 'r', 's', '2026-01-01', '2026-01-01')", "(2, 'C001120', 'r', 's', '2026-01-01', '2026-01-01')"):
        with pytest.raises(sa.exc.IntegrityError), engine.begin() as c:
            c.exec_driver_sql(f"insert into politician_alias_overrides (politician_id, bioguide_id, reason, source, reviewed_at, created_at) values {sql}")


def test_downgrade_removes_only_the_new_pieces(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, bioguide_id, created_at) values (1, 'k', 'n', 'house', 'D000399', '2026-01-01')")
    command.downgrade(cfg, "0006")
    assert "politician_alias_overrides" not in sa.inspect(engine).get_table_names()
    assert "enrichment_method" not in {c["name"] for c in sa.inspect(engine).get_columns("politicians")}
    with engine.connect() as c:
        assert c.exec_driver_sql("select bioguide_id from politicians").scalar() == "D000399"
