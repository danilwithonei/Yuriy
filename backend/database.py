from sqlmodel import SQLModel, create_engine
from core.logger import logger
import os
from sqlalchemy.pool import StaticPool

TESTING = os.getenv("TESTING", "").lower() in ("1", "true")
DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./db/auth.db")
kwargs = {"echo": False, "connect_args": {"check_same_thread": False}}
if TESTING:
    DATABASE_URL = "sqlite:///:memory:"
    kwargs["poolclass"] = StaticPool
os.makedirs("./db", exist_ok=True)
engine = create_engine(DATABASE_URL, **kwargs)

def create_db_and_tables():
    import models
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    logger.info("Auth database tables created")
