from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    role: str  # "client" or "lawyer"

class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="user.id")
    status: str = Field(default="open")  # "open", "researching", "ready", "closed"
    case_file: Optional[str] = None  # Markdown report
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id")
    sender_role: str  # "client", "ai_intake", "lawyer", "ai_case"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
