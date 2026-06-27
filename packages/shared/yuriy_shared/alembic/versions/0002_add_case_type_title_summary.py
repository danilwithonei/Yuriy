"""add case_type, title, summary to case (lawyer-service migration)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if "case" not in inspector.get_table_names():
        return
    columns = [c["name"] for c in inspector.get_columns("case")]
    with op.batch_alter_table("case") as batch_op:
        if "case_type" not in columns:
            batch_op.add_column(
                sa.Column("case_type", sa.String(), nullable=False, server_default="intake")
            )
        if "title" not in columns:
            batch_op.add_column(sa.Column("title", sa.String(), nullable=True))
        if "summary" not in columns:
            batch_op.add_column(sa.Column("summary", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if "case" not in inspector.get_table_names():
        return
    columns = [c["name"] for c in inspector.get_columns("case")]
    with op.batch_alter_table("case") as batch_op:
        if "case_type" in columns:
            batch_op.drop_column("case_type")
        if "title" in columns:
            batch_op.drop_column("title")
        if "summary" in columns:
            batch_op.drop_column("summary")
