from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(foreign_key="case.id")
    source: str = Field(default="system")
    sender_role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
