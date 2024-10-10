from sqlmodel import Field, SQLModel
from typing import Optional

class Incidente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    user_id: int