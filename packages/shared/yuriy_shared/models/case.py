from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
import uuid


class Case(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    client_id: int = Field(foreign_key="user.id")
    lawyer_id: Optional[int] = None
    source: str = Field(default="system")
    case_type: str = Field(default="intake")
    status: str = Field(default="open")
    case_file: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    pinned: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
