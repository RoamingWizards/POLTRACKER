"""Migration 0011 adds human-review fields to committee_industry_mappings. Existing rows become needs_review, never reviewed."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
NEW = {"review_status", "reviewed_by", "review_note", "jurisdiction_basis"}


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm11.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("committee_industry_mappings")}


def seed(engine):
    with engine.begin() as c:
        c.exec_driver_sql("insert into committee_industry_mappings (id, chamber, committee_code, committee_name, sic_start, sic_end, relevance_level, rationale, source_url, "
                          "mapping_version, created_at) values (1, 'house', 'AS00', 'Armed Services', 3720, 3729, 'direct', 'r', 'https://x', '2026.1-draft', '2026-01-01')")


def test_existing_rows_become_needs_review_and_are_never_marked_reviewed(db):
    engine, cfg = db
    command.upgrade(cfg, "0010")
    seed(engine)
    assert not NEW & cols(engine)
    command.upgrade(cfg, "head")
    assert NEW <= cols(engine)
    with engine.connect() as c:
        row = c.exec_driver_sql("select id, sic_start, sic_end, relevance_level, rationale, reviewed_at, review_status, reviewed_by, review_note, jurisdiction_basis "
                                "from committee_industry_mappings").one()
        assert tuple(row) == (1, 3720, 3729, "direct", "r", None, "needs_review", None, None, None)
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0013"


def test_downgrade_removes_only_the_review_columns_and_keeps_the_mapping(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    seed_row = "insert into committee_industry_mappings (id, chamber, committee_code, committee_name, sic_start, sic_end, relevance_level, rationale, source_url, mapping_version, created_at, review_status) values (1, 'house', 'AS00', 'Armed Services', 3720, 3729, 'direct', 'r', 'https://x', 'v', '2026-01-01', 'reviewed')"
    with engine.begin() as c:
        c.exec_driver_sql(seed_row)
    command.downgrade(cfg, "0010")
    assert not NEW & cols(engine)
    with engine.connect() as c:
        assert tuple(c.exec_driver_sql("select id, sic_start, sic_end, relevance_level from committee_industry_mappings").one()) == (1, 3720, 3729, "direct")
    command.upgrade(cfg, "head")


def test_the_model_matches_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name
