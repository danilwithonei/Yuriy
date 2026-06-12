import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

# Using SQLite for simplicity in development, can be easily changed to Postgres
sqlite_url = "sqlite:///./database.db"
# postgres_url = os.getenv("DATABASE_URL")

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
