import os

from yuriy_shared.database import create_db_and_tables as _create_tables
from yuriy_shared.database import create_engine as _make_engine

from core.logger import logger

TESTING = os.getenv("TESTING", "").lower() in ("1", "true")
DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./db/auth.db")
engine = _make_engine(DATABASE_URL, testing=TESTING)


def create_db_and_tables():
    _create_tables(engine)
    logger.info("Auth database tables created")
