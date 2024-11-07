from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum
from datetime import date
import random
import string


class Categoria(str, Enum):
    acceso = "acceso"
    funcionamiento = "funcionamiento"
    queja = "queja"
    retiro = "retiro"


class Prioridad(str, Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class Canal(str, Enum):
    llamada = "llamada"
    correo = "correo"
    aplicacion = "aplicacion"


class Estado(str, Enum):
    abierto = "abierto"
    cerrado = "cerrado"
    escalado = "escalado"


class Incidente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    categoria: Categoria
    prioridad: Prioridad
    canal: Canal
    cliente_id: int
    estado: Estado
    fecha_creacion: date = Field(default_factory=date.today)
    fecha_cierre: Optional[date] = None
    solucion: Optional[str] = Field(sa_column=Column(TEXT))
    radicado: str = Field(default_factory=lambda: ''.join(random.choices(string.ascii_letters + string.digits, k=8)), index=True)
    identificacion_usuario: str = Field(max_length=15, nullable=True)
 

class ProblemaComun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    categoria: Categoria
    solucion: str = Field(sa_column=Column(TEXT))