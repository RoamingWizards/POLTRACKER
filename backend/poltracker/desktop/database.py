"""Create or upgrade the app's SQLite database safely.

Rules: never overwrite an existing database; back it up before any schema upgrade; refuse (and say why) rather than
touch a file that is not a recognisable POLTRACKER database or that was made by a newer version of the app.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

log = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """A problem the user can act on; the message is shown in the app."""


@dataclass(frozen=True)
class DatabaseState:
    exists: bool
    has_tables: bool
    revision: str | None


@dataclass(frozen=True)
class PrepareResult:
    created: bool
    upgraded: bool
    from_revision: str | None
    to_revision: str
    backup: Path | None


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def inspect_database(path: Path) -> DatabaseState:
    if not path.exists() or path.stat().st_size == 0:
        return DatabaseState(exists=path.exists(), has_tables=False, revision=None)
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in conn.execute("select name from sqlite_master where type = 'table' and name not like 'sqlite_%'")}
            revision = None
            if "alembic_version" in tables:
                row = conn.execute("select version_num from alembic_version").fetchone()
                revision = row[0] if row else None
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise DatabaseError(f"{path} is not a readable SQLite database ({exc}). It was left untouched.") from exc
    return DatabaseState(exists=True, has_tables=bool(tables - {"alembic_version"}), revision=revision)


def alembic_config(migrations: Path, url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))  # configparser treats % specially
    return cfg


def known_revisions(migrations: Path) -> tuple[str, set[str]]:
    script = ScriptDirectory.from_config(alembic_config(migrations, "sqlite://"))
    return script.get_current_head(), {r.revision for r in script.walk_revisions()}


def backup_database(path: Path, revision: str | None) -> Path:
    """Consistent copy (SQLite backup API) next to the database; never overwrites an earlier backup."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.backup-{revision or 'unversioned'}-{stamp}")
    n = 1
    while dest.exists():
        dest = path.with_name(f"{path.name}.backup-{revision or 'unversioned'}-{stamp}-{n}")
        n += 1
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        out = sqlite3.connect(dest)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    return dest


def prepare_database(path: Path, migrations: Path) -> PrepareResult:
    head, revisions = known_revisions(migrations)
    state = inspect_database(path)
    backup = None
    created = not (state.exists and state.has_tables)

    if state.has_tables:
        if state.revision is None:
            raise DatabaseError(
                f"{path} has tables but no migration history, so it is not a database this app created. It was left untouched."
            )
        if state.revision not in revisions:
            raise DatabaseError(
                f"{path} was created by a newer version of POLTRACKER (schema {state.revision}). It was left untouched."
            )
        if state.revision == head:
            log.info("database %s already at schema %s", path, head)
            return PrepareResult(False, False, state.revision, head, None)
        backup = backup_database(path, state.revision)
        log.info("backed up %s to %s before upgrading %s -> %s", path, backup, state.revision, head)

    path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(migrations, sqlite_url(path)), "head")
    after = inspect_database(path)
    if after.revision != head:
        raise DatabaseError(f"Migration finished at schema {after.revision!r}, expected {head!r}.")
    log.info("database %s ready at schema %s (%s)", path, head, "created" if created else "upgraded")
    return PrepareResult(created, not created, state.revision, head, backup)
