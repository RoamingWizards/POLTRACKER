"""Migration 0017 adds the AI provider to cached trade-context explanations: existing rows become 'openai', nothing else changes, and uniqueness now includes the provider."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from poltracker.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm17.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def insert(c, id_, provider=None, model="m"):
    cols = "id, trade_id, context_version, mapping_version, prompt_version, " + ("provider, " if provider else "") + \
        "model, input_hash, context_digest, generated_for, headline, summary, signals_json, limitations, created_at"
    vals = f"{id_}, 1, 'cv', 'mv', '3', " + (f"'{provider}', " if provider else "") + f"'{model}', 'h', 'd', 'flagged', 'H', 'S', '[]', 'L', '2026-01-01'"
    c.exec_driver_sql(f"insert into trade_context_analysis ({cols}) values ({vals})")


def test_existing_explanations_are_backfilled_as_openai_and_unchanged(db):
    engine, cfg = db
    command.upgrade(cfg, "0016")
    with engine.begin() as c:
        insert(c, 1)
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        row = c.exec_driver_sql("select provider, model, headline, summary from trade_context_analysis").one()
        assert tuple(row) == ("openai", "m", "H", "S")
        insert(c, 2, "anthropic")  # same trade, context, mapping, prompt and model name: allowed for another provider
        with pytest.raises(sa.exc.IntegrityError):
            insert(c, 3, "openai")  # but not twice for the same provider


def test_downgrade_keeps_openai_rows_and_drops_other_providers(db):
    engine, cfg = db
    command.upgrade(cfg, "head")
    with engine.begin() as c:
        insert(c, 1, "openai")
        insert(c, 2, "anthropic")
    command.downgrade(cfg, "0016")
    with engine.connect() as c:
        assert [r[0] for r in c.exec_driver_sql("select id from trade_context_analysis")] == [1]
        assert "provider" not in {col["name"] for col in sa.inspect(engine).get_columns("trade_context_analysis")}
