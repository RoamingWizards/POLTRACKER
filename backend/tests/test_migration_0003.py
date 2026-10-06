"""Migration 0003 on a database shaped like the one that existed before it."""

import importlib.util
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from poltracker.config import get_settings
from poltracker.domain import TradeIn
from poltracker.ingest import store_trades
from poltracker.normalize import fingerprint

ROOT = Path(__file__).resolve().parents[2]


def load_migration():
    spec = importlib.util.spec_from_file_location("m0003", ROOT / "migrations/versions/0003_merge_politician_name_variants.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(cfg, "0002")
    yield url, cfg
    get_settings.cache_clear()


def seed_legacy(engine, mig):
    """Politicians/trades as the pre-0003 code stored them (old key, old fingerprints)."""
    people = [
        (1, "John J McGuire", "house"),
        (2, "John McGuire", "house"),
        (3, "Scott Scott Franklin", "house"),
        (4, "Gary C Peters", "senate"),
        (5, "Dan Crenshaw", "house"),
        (6, "Daniel Crenshaw", "house"),  # nickname variants must NOT merge
    ]
    trade_specs = [  # (politician id, ticker, tx date, amount_min) -- two identical lines for politician 2
        (1, "AAPL", date(2026, 1, 5), 1001),
        (1, "MSFT", date(2026, 1, 6), 1001),
        (2, "AAPL", date(2026, 2, 1), 1001),
        (2, "AAPL", date(2026, 2, 1), 1001),
        (2, "NVDA", date(2026, 2, 2), 15001),
        (3, "HD", date(2026, 3, 1), 1001),
        (4, "XOM", date(2026, 3, 2), 1001),
        (5, "TSLA", date(2026, 3, 3), 1001),
        (6, "TSLA", date(2026, 3, 3), 1001),
    ]
    names = {pid: (name, ch) for pid, name, ch in people}
    rows = []
    for i, (pid, tk, txd, amin) in enumerate(trade_specs, start=1):
        name, ch = names[pid]
        rows.append(dict(id=i, politician_id=pid, politician_name=name, chamber=ch, ticker=tk, asset_name=tk,
                         transaction_type="buy", transaction_date=txd, disclosure_date=date(2026, 4, 1),
                         amount_min=amin, amount_max=amin * 10))
    fps = mig.compute_fingerprints(rows, lambda r: mig._old_key(r["politician_name"], r["chamber"]))
    now = datetime(2026, 1, 1)
    with engine.begin() as c:
        for pid, name, ch in people:
            c.execute(sa.text("insert into politicians (id, canonical_key, name, chamber, created_at) values (:i,:k,:n,:c,:t)"),
                      dict(i=pid, k=mig._old_key(name, ch), n=name, c=ch, t=now))
        for r in rows:
            c.execute(sa.text(
                "insert into trades (id, source, fingerprint, politician_id, politician_name, chamber, ticker, asset_name, "
                "transaction_type, transaction_date, disclosure_date, amount_min, amount_max, created_at) values "
                "(:id,'congressinvests',:fp,:politician_id,:politician_name,:chamber,:ticker,:asset_name,:transaction_type,"
                ":transaction_date,:disclosure_date,:amount_min,:amount_max,:now)"), dict(r, fp=fps[r["id"]], now=now))
    return rows


def test_migration_merges_safe_variants_only(legacy_db):
    url, cfg = legacy_db
    mig = load_migration()
    engine = sa.create_engine(url)
    seed_legacy(engine, mig)
    command.upgrade(cfg, "head")

    with engine.connect() as c:
        pols = {r.name: r for r in c.execute(sa.text("select * from politicians"))}
        # McGuire merged (survivor = the variant with more trades), Franklin cleaned,
        # Peters untouched, the two Crenshaws deliberately kept apart.
        assert set(pols) == {"John McGuire", "Scott Franklin", "Gary C Peters", "Dan Crenshaw", "Daniel Crenshaw"}
        assert c.execute(sa.text("select count(*) from trades where politician_id=:i"), dict(i=pols["John McGuire"].id)).scalar() == 5
        assert c.execute(sa.text("select count(*) from trades where politician_name='John J McGuire'")).scalar() == 0
        assert c.execute(sa.text("select count(*) from trades")).scalar() == 9  # nothing lost
        assert c.execute(sa.text("select count(distinct fingerprint) from trades")).scalar() == 9
        assert c.execute(sa.text("select count(*) from trades where fingerprint like 'tmp-%'")).scalar() == 0


def test_migrated_fingerprints_match_fresh_ingestion(legacy_db):
    """After migrating, re-ingesting the same disclosures must insert nothing."""
    url, cfg = legacy_db
    mig = load_migration()
    engine = sa.create_engine(url)
    rows = seed_legacy(engine, mig)
    command.upgrade(cfg, "head")

    # What the provider would deliver again on the next poll, using the NEW normalisation.
    from poltracker.normalize import normalize_name

    trades = [
        TradeIn(source="congressinvests", politician_name=normalize_name(r["politician_name"]), chamber=r["chamber"],
                transaction_type=r["transaction_type"], transaction_date=r["transaction_date"], ticker=r["ticker"],
                asset_name=r["asset_name"], disclosure_date=r["disclosure_date"], amount_min=r["amount_min"],
                amount_max=r["amount_max"])
        for r in rows
    ]
    with sessionmaker(engine, expire_on_commit=False)() as s:
        assert store_trades(s, trades, Counter()) == 0
        s.rollback()

    # And the migration's frozen fingerprint recipe agrees with the live one.
    seen = Counter()
    for t in trades:
        base = fingerprint(t, 0)
        fp = fingerprint(t, seen[base])
        seen[base] += 1
        with engine.connect() as c:
            assert c.execute(sa.text("select count(*) from trades where fingerprint=:f"), dict(f=fp)).scalar() == 1


def test_migration_cannot_be_downgraded(legacy_db):
    url, cfg = legacy_db
    command.upgrade(cfg, "head")
    with pytest.raises(NotImplementedError):
        command.downgrade(cfg, "0002")


def test_migration_runs_on_an_empty_database(legacy_db):
    """A fresh install goes 0001 -> head with no rows to migrate."""
    url, cfg = legacy_db
    command.upgrade(cfg, "head")
    with sa.create_engine(url).connect() as c:
        assert c.execute(sa.text("select count(*) from trades")).scalar() == 0
