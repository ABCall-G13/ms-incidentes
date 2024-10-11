from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum

class Categoria(str, Enum):
    acceso = "acceso"
    funcionamiento = "funcionamiento"

class Prioridad(str, Enum):
    alta = "alta"
    media = "media"
    baja = "baja"

class Canal(str, Enum):
    llamada = "llamada"
    correo = "correo"

class Incidente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    categoria: Categoria
    prioridad: Prioridad
    canal: Canal
    cliente_id: int