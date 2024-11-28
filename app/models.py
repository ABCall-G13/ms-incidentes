from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum
from datetime import date, datetime
import secrets
import string
import pytz


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


def bogota_date():
    bogota_tz = pytz.timezone('America/Bogota')
    return datetime.now(bogota_tz).date()

class Incidente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    categoria: Categoria
    prioridad: Prioridad
    canal: Canal
    cliente_id: int
    estado: Estado
    fecha_creacion: Optional[date] = Field(default_factory=bogota_date)
    fecha_cierre: Optional[date] = None
    solucion: Optional[str] = Field(sa_column=Column(TEXT))
    radicado: str = Field(
        default_factory=lambda: ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8)),
        index=True
    )
    identificacion_usuario: str = Field(max_length=15, nullable=True)

class ProblemaComun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    categoria: Categoria
    solucion: str = Field(sa_column=Column(TEXT))
    cliente_id: int

class LogIncidente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    incidente_id: int = Field(index=True)
    cuerpo_completo: str = Field(sa_column=Column(TEXT))
    fecha_cambio: datetime = Field(default_factory=datetime.utcnow)
    origen_cambio: str  