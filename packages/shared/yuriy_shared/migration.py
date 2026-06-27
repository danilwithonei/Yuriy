import os
from sqlmodel import create_engine
from sqlalchemy import inspect


def run_migrations(database_url: str, alembic_ini_path: str | None = None):
    from alembic.config import Config
    from alembic import command

    ini_path = alembic_ini_path or os.path.join(
        os.path.dirname(__file__), "..", "alembic.ini"
    )
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", database_url)

    engine = create_engine(database_url)
    with engine.connect() as conn:
        inspector = inspect(conn)
        has_alembic = "alembic_version" in inspector.get_table_names()
        has_tables = bool(inspector.get_table_names())

    if has_alembic:
        command.upgrade(cfg, "head")
    elif has_tables:
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
