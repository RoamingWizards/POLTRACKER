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

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def make_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(engine or make_engine(), expire_on_commit=False)
