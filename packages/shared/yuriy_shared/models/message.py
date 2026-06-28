from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    case_id: str = Field(foreign_key="case.id")
    source: str = Field(default="system")
    sender_role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
