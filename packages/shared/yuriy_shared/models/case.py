import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Case(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    client_id: int = Field(foreign_key="user.id")
    lawyer_id: int | None = None
    source: str = Field(default="system")
    case_type: str = Field(default="intake")
    status: str = Field(default="open")
    case_file: str | None = None
    title: str | None = None
    summary: str | None = None
    pinned: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
