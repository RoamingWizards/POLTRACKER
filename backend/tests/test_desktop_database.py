"""The desktop database bootstrap must create, upgrade and refuse safely, and never harm an existing file."""

import hashlib
import sqlite3
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command

from poltracker.desktop import database as dbm
from poltracker.desktop import paths

MIGRATIONS = paths.migrations_dir()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_db_at(path: Path, revision: str) -> None:
    command.upgrade(dbm.alembic_config(MIGRATIONS, dbm.sqlite_url(path)), revision)


def test_a_new_database_is_created_at_head(tmp_path):
    db = tmp_path / "nested" / "poltracker.db"
    result = dbm.prepare_database(db, MIGRATIONS)
    head, _ = dbm.known_revisions(MIGRATIONS)
    assert (result.created, result.upgraded, result.to_revision, result.backup) == (True, False, head, None)
    assert dbm.inspect_database(db).revision == head
    tables = {r[0] for r in sqlite3.connect(db).execute("select name from sqlite_master where type='table'")}
    assert {"trades", "politicians", "securities", "price_bars", "ingest_state", "alembic_version"} <= tables


def test_an_empty_zero_byte_file_is_treated_as_new(tmp_path):
    db = tmp_path / "poltracker.db"
    db.touch()
    assert dbm.prepare_database(db, MIGRATIONS).created is True


def test_a_database_already_at_head_is_not_touched_at_all(tmp_path):
    db = tmp_path / "poltracker.db"
    dbm.prepare_database(db, MIGRATIONS)
    before = sha(db)
    result = dbm.prepare_database(db, MIGRATIONS)
    assert (result.created, result.upgraded, result.backup) == (False, False, None)
    assert sha(db) == before  # byte-for-byte identical: not even opened for writing


def test_an_older_database_is_backed_up_then_upgraded_with_data_intact(tmp_path):
    db = tmp_path / "poltracker.db"
    make_db_at(db, "0004")
    with sqlite3.connect(db) as conn:
        conn.execute("insert into ingest_state (source, backfill_complete, updated_at) values ('congressinvests', 1, '2026-01-01 00:00:00')")
    original = sha(db)

    result = dbm.prepare_database(db, MIGRATIONS)

    assert result.upgraded and result.from_revision == "0004" and result.to_revision == "0014"
    assert result.backup and result.backup.exists() and sha(result.backup) != ""  # a real backup file
    assert dbm.inspect_database(result.backup).revision == "0004"  # the backup is the pre-upgrade state
    assert sqlite3.connect(result.backup).execute("select count(*) from ingest_state").fetchone()[0] == 1
    row = sqlite3.connect(db).execute("select source, backfill_complete, last_success_at from ingest_state").fetchone()
    assert row == ("congressinvests", 1, None)  # data survived, new column empty
    assert sha(db) != original


def test_each_backup_gets_its_own_name(tmp_path):
    db = tmp_path / "poltracker.db"
    make_db_at(db, "0004")
    first = dbm.backup_database(db, "0004")
    second = dbm.backup_database(db, "0004")
    assert first != second and first.exists() and second.exists()


def test_a_database_with_tables_but_no_history_is_refused_and_untouched(tmp_path):
    db = tmp_path / "other.db"
    with sqlite3.connect(db) as conn:
        conn.execute("create table notes (id integer primary key, body text)")
        conn.execute("insert into notes (body) values ('keep me')")
    before = sha(db)
    with pytest.raises(dbm.DatabaseError, match="not a database this app created"):
        dbm.prepare_database(db, MIGRATIONS)
    assert sha(db) == before


def test_a_database_from_a_newer_app_is_refused_and_untouched(tmp_path):
    db = tmp_path / "poltracker.db"
    dbm.prepare_database(db, MIGRATIONS)
    with sqlite3.connect(db) as conn:
        conn.execute("update alembic_version set version_num = '9999'")
    before = sha(db)
    with pytest.raises(dbm.DatabaseError, match="newer version"):
        dbm.prepare_database(db, MIGRATIONS)
    assert sha(db) == before


def test_a_corrupt_file_is_refused_and_untouched(tmp_path):
    db = tmp_path / "poltracker.db"
    db.write_bytes(b"this is not a sqlite database" * 50)
    before = sha(db)
    with pytest.raises(dbm.DatabaseError, match="not a readable SQLite database"):
        dbm.prepare_database(db, MIGRATIONS)
    assert sha(db) == before


def test_a_path_containing_a_percent_sign_still_migrates(tmp_path):
    db = tmp_path / "100% data" / "poltracker.db"  # configparser would choke on a raw %
    assert dbm.prepare_database(db, MIGRATIONS).created is True
