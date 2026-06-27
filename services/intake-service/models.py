from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime
import uuid

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    source: str = Field(index=True) # "telegram", "max", "frontend"
    username: str = Field(index=True)
    role: str  # "client" or "lawyer"

class Case(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    client_id: int = Field(foreign_key="user.id")
    lawyer_id: Optional[int] = None
    source: str = Field(default="system")
    case_type: str = Field(default="intake")  # "intake" | "direct"
    status: str = Field(default="open")  # "open", "researching", "ready", "closed"
    case_file: Optional[str] = None  # Markdown report
    title: Optional[str] = None  # Название дела (генер. LLM)
    summary: Optional[str] = None  # Краткое описание дела
    pinned: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(foreign_key="case.id")
    source: str = Field(default="system")
    # Роли: 
    # "client" - клиент (ТГ/MAX), 
    # "ai_intake" - ии-помощник (бот-приемщик), 
    # "lawyer" - юрист (веб-приложение), 
    # "ai_case" - ии-ассистент (ассистент юриста в веб-приложении)
    sender_role: str  
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
