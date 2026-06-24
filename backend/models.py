from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class Lawyer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
