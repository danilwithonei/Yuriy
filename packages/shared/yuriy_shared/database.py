import os
from sqlmodel import SQLModel, create_engine as _create_engine, Session
from sqlalchemy.pool import StaticPool


def create_engine(database_url: str | None = None, *, testing: bool = False):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./db/data.db")
    kwargs = {"echo": False, "connect_args": {"check_same_thread": False}}
    if testing or os.getenv("TESTING", "").lower() in ("1", "true"):
        url = "sqlite:///:memory:"
        kwargs["poolclass"] = StaticPool
    os.makedirs("./db", exist_ok=True)
    return _create_engine(url, **kwargs)


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def get_session(engine):
    def _get_session():
        with Session(engine) as session:
            yield session
    return _get_session
