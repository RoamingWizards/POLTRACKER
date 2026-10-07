"""Copy an existing poltracker.db into the app's data folder, verified, without touching the original.

    python -m poltracker.desktop.importer [SOURCE] [--replace]

SOURCE defaults to ./poltracker.db. The original is opened read-only and its bytes are checked before and after, so it is
provably unchanged. If the app already has a database, nothing happens unless --replace is given, and then the old one is
moved aside (never deleted).
"""

import argparse
import hashlib
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import paths

TABLES = ["politicians", "securities", "trades", "price_bars", "ingest_state"]
ORDER = {"politicians": "id", "securities": "id", "trades": "id", "price_bars": "security_id, date", "ingest_state": "source"}


class ImportError_(RuntimeError):
    pass


@dataclass
class ImportReport:
    source: Path
    destination: Path
    counts: dict[str, int]
    hashes_match: bool
    source_unchanged: bool
    replaced_backup: Path | None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path: Path) -> dict[str, tuple[int, str]]:
    """Row count and an order-stable content hash per table, over the columns every schema version has."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        out = {}
        for table in TABLES:
            cols = [r[1] for r in conn.execute(f"pragma table_info({table})") if r[1] != "last_success_at"]
            digest, n = hashlib.sha256(), 0
            for row in conn.execute(f"select {', '.join(cols)} from {table} order by {ORDER[table]}"):
                digest.update(repr(row).encode())
                n += 1
            out[table] = (n, digest.hexdigest()[:16])
        return out
    finally:
        conn.close()


def import_database(source: Path, destination: Path | None = None, *, replace: bool = False) -> ImportReport:
    destination = destination or paths.database_path()
    source = source.resolve()
    if not source.is_file():
        raise ImportError_(f"{source} does not exist.")
    if source == destination.resolve():
        raise ImportError_("The source and the destination are the same file.")

    source_hash_before = sha256(source)
    try:
        conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        try:
            ok = conn.execute("pragma integrity_check").fetchone()[0]
            has_versions = conn.execute("select 1 from sqlite_master where name = 'alembic_version'").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ImportError_(f"{source} is not a readable SQLite database: {exc}") from exc
    if ok != "ok" or not has_versions:
        raise ImportError_(f"{source} failed validation (integrity: {ok}; migration history present: {bool(has_versions)}).")

    backup = None
    if destination.exists() and destination.stat().st_size > 0:
        if not replace:
            raise ImportError_(f"{destination} already exists. Nothing was changed; pass --replace to move it aside and import.")
        backup = destination.with_name(f"{destination.name}.replaced-{datetime.now():%Y%m%d-%H%M%S}")
        destination.rename(backup)
        for suffix in ("-wal", "-shm"):  # leftovers of a write-ahead-log database belong with the moved file
            leftover = destination.with_name(destination.name + suffix)
            if leftover.exists():
                leftover.rename(backup.with_name(backup.name + suffix))

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".importing")
    temp.unlink(missing_ok=True)
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        out = sqlite3.connect(temp)
        try:
            src.backup(out)  # consistent snapshot even if another process has the file open
        finally:
            out.close()
    finally:
        src.close()

    before, after = fingerprint(source), fingerprint(temp)
    if before != after:
        temp.unlink(missing_ok=True)
        raise ImportError_("Verification failed: the copy does not match the original. Nothing was installed.")
    temp.rename(destination)
    return ImportReport(
        source, destination, {t: n for t, (n, _h) in after.items()}, True, sha256(source) == source_hash_before, backup
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an existing poltracker.db into the POLTRACKER app's data folder")
    parser.add_argument("source", nargs="?", default="poltracker.db", type=Path)
    parser.add_argument("--replace", action="store_true", help="move an existing app database aside and import over it")
    args = parser.parse_args(argv)
    try:
        report = import_database(args.source, replace=args.replace)
    except ImportError_ as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1
    print(f"Imported {report.source}\n      -> {report.destination}")
    for table, n in report.counts.items():
        print(f"  {table:13s} {n:>9,} rows (verified identical)")
    print(f"  original file unchanged: {report.source_unchanged}")
    if report.replaced_backup:
        print(f"  previous app database kept at: {report.replaced_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
