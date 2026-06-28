import os

from sqlmodel import Session
from yuriy_shared.database import create_db_and_tables as _create_tables
from yuriy_shared.database import create_engine as _make_engine

DATABASE_URL = os.getenv("AGENT_DATABASE_URL", "sqlite:///./db/agent_database.db")
engine = _make_engine(DATABASE_URL)


def create_db_and_tables():
    _create_tables(engine)


def get_session():
    with Session(engine) as session:
        yield session
