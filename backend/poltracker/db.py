import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings, normalize_database_url


def make_engine(url: str | None = None) -> Engine:
    url = normalize_database_url(url or get_settings().database_url)
    kwargs: dict = {}
    if url.startswith("postgresql"):
        # Serverless Postgres (e.g. Neon) suspends idle compute and drops connections: check before use,
        # recycle early, and keep the pool small for a 512 MB host.
        kwargs = {"pool_pre_ping": True, "pool_size": 3, "max_overflow": 2, "pool_recycle": 240}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        # The desktop app reads from the API while a background refresh writes, so wait for locks instead of failing
        # and (desktop only, set by the launcher) use write-ahead logging so readers never block the writer.
        wal = os.environ.get("POLTRACKER_SQLITE_WAL") == "1"

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
            dbapi_conn.execute("PRAGMA busy_timeout=30000")
            if wal:
                dbapi_conn.execute("PRAGMA journal_mode=WAL")
                dbapi_conn.execute("PRAGMA synchronous=NORMAL")

    return engine


def make_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(engine or make_engine(), expire_on_commit=False)
