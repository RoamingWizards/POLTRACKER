"""Importing an existing poltracker.db must copy it verifiably and leave the original untouched."""

import hashlib
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from poltracker.db import make_engine
from poltracker.desktop import database as dbm
from poltracker.desktop import importer, paths
from poltracker.domain import TradeIn
from poltracker.ingest import store_trades


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def source_db(tmp_path) -> Path:
    path = tmp_path / "src" / "poltracker.db"
    dbm.prepare_database(path, paths.migrations_dir())
    engine = make_engine(dbm.sqlite_url(path))
    trades = [
        TradeIn(source="congressinvests", politician_name=f"Member {i % 3}", chamber="house", transaction_type="buy",
                transaction_date=date(2026, 1, 1 + i), ticker=f"T{i % 4}", asset_name="Co", disclosure_date=date(2026, 2, 1),
                amount_min=1001, amount_max=15000)
        for i in range(12)
    ]
    with sessionmaker(engine, expire_on_commit=False)() as s:
        store_trades(s, trades, Counter())
        s.commit()
    engine.dispose()
    with sqlite3.connect(path) as conn:  # an ingest_state row like a real database has
        conn.execute("insert or replace into ingest_state (source, backfill_complete, updated_at) values ('congressinvests', 1, '2026-01-01 00:00:00')")
    return path


def test_import_copies_everything_and_the_original_is_byte_identical(source_db, tmp_path):
    dest = tmp_path / "app" / "poltracker.db"
    before = sha(source_db)
    report = importer.import_database(source_db, dest)
    assert report.hashes_match and report.source_unchanged
    assert sha(source_db) == before
    assert report.counts == {"politicians": 3, "securities": 4, "trades": 12, "price_bars": 0, "ingest_state": 1}
    assert importer.fingerprint(source_db) == importer.fingerprint(dest)
    assert dbm.inspect_database(dest).revision == dbm.inspect_database(source_db).revision


def test_import_refuses_to_overwrite_an_existing_app_database(source_db, tmp_path):
    dest = tmp_path / "poltracker.db"
    dest.write_bytes(b"SQLite format 3\x00" + b"x" * 200)
    before = sha(dest)
    with pytest.raises(importer.ImportError_, match="already exists"):
        importer.import_database(source_db, dest)
    assert sha(dest) == before


def test_replace_moves_the_old_database_aside_instead_of_deleting_it(source_db, tmp_path):
    dest = tmp_path / "poltracker.db"
    dbm.prepare_database(dest, paths.migrations_dir())
    old = sha(dest)
    report = importer.import_database(source_db, dest, replace=True)
    assert report.replaced_backup and report.replaced_backup.exists() and sha(report.replaced_backup) == old
    assert importer.fingerprint(source_db) == importer.fingerprint(dest)


def test_import_rejects_a_missing_or_foreign_source(tmp_path):
    with pytest.raises(importer.ImportError_, match="does not exist"):
        importer.import_database(tmp_path / "nope.db", tmp_path / "out.db")
    foreign = tmp_path / "foreign.db"
    with sqlite3.connect(foreign) as conn:
        conn.execute("create table t (x)")
    with pytest.raises(importer.ImportError_, match="failed validation"):
        importer.import_database(foreign, tmp_path / "out.db")
    assert not (tmp_path / "out.db").exists()


def test_import_rejects_importing_a_file_onto_itself(source_db):
    with pytest.raises(importer.ImportError_, match="same file"):
        importer.import_database(source_db, source_db)


def test_a_failed_verification_installs_nothing(source_db, tmp_path, monkeypatch):
    dest = tmp_path / "poltracker.db"
    real = importer.fingerprint
    calls = {"n": 0}

    def tampered(path):
        calls["n"] += 1
        data = real(path)
        if calls["n"] == 2:  # the copy "differs" from the original
            data["trades"] = (data["trades"][0], "deadbeefdeadbeef")
        return data

    monkeypatch.setattr(importer, "fingerprint", tampered)
    with pytest.raises(importer.ImportError_, match="Verification failed"):
        importer.import_database(source_db, dest)
    assert not dest.exists() and not dest.with_name(dest.name + ".importing").exists()


def test_the_command_line_reports_success_and_failure(source_db, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(paths.HOME_ENV, str(tmp_path / "home"))
    assert importer.main([str(source_db)]) == 0
    assert "verified identical" in capsys.readouterr().out
    assert importer.main([str(source_db)]) == 1  # second time: the app database now exists
    assert "already exists" in capsys.readouterr().err
