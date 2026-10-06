import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from poltracker.models import Base

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def recent_body() -> dict:
    return json.loads((FIXTURES / "congressinvests_recent.json").read_text())


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
