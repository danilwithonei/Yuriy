from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    source: str = Field(index=True)
    username: str = Field(index=True)
    role: str
