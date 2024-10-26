from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.models import Canal, Categoria, Estado, Incidente, Prioridad
from app.database import create_incidente_cache, get_session, get_redis_client, obtener_incidente_cache, obtener_incidente_por_radicado, publisher, topic_path, get_session_replica
from sqlmodel import Session, select
from redis import Redis
import json

router = APIRouter()


@router.get("/")
async def health():
    return {"status": "ok"}


@router.post("/incidente", response_model=Incidente)
async def crear_incidente(
    event_data: Incidente,
    session: Session = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client)
):
    event_data.id = None
    try:
        incidente = create_incidente_cache(event_data, session, redis_client)
        message_data = incidente.model_dump()
        print("TEST")
        print(json.dumps(message_data).encode("utf-8"))
        future = publisher.publish(topic_path, json.dumps(message_data).encode("utf-8"))
        print("FUTURE")
        print(future)
        message_id = future.result()
        return incidente
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidente/{incidente_id}", response_model=Incidente)
async def obtener_incidente(
    incidente_id: int,
    session: Session = Depends(get_session_replica),
    redis_client: Redis = Depends(get_redis_client)
):
    incidente = obtener_incidente_cache(incidente_id, session, redis_client)
    if incidente:
        return incidente
    else:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")


# Nuevo endpoint para obtener todos los incidentes
@router.get("/incidentes", response_model=list[Incidente])
async def obtener_todos_los_incidentes(
    session: Session = Depends(get_session_replica)
):
    try:
        # Consulta para obtener todos los incidentes
        statement = select(Incidente)
        results = session.exec(statement).all()  # Ejecutar la consulta

        return results  # Devuelve la lista de incidentes
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al obtener incidentes")


@router.get("/incidentes/fields")
async def obtener_valores_permitidos():
    return {
        "categoria": [categoria.value for categoria in Categoria],
        "prioridad": [prioridad.value for prioridad in Prioridad],
        "canal": [canal.value for canal in Canal],
        "estado": [estado.value for estado in Estado]
    }


class SolucionRequest(BaseModel):
    solucion: str
# Ruta para solucionar un incidente


@router.put("/incidente/{incidente_id}/solucionar", response_model=Incidente)
async def solucionar_incidente(
    incidente_id: int,
    event_data: SolucionRequest,
    session: Session = Depends(get_session)
):

    incidente_existente = session.get(Incidente, incidente_id)

    if not incidente_existente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    # Actualizar la solución y cambiar el estado a "cerrado"
    incidente_existente.solucion = event_data.solucion
    incidente_existente.estado = "cerrado"
    incidente_existente.fecha_cierre = date.today()
    session.add(incidente_existente)
    session.commit()
    session.refresh(incidente_existente)

    return incidente_existente

# Ruta para escalar un incidente
@router.put("/incidente/{incidente_id}/escalar", response_model=Incidente)
async def escalar_incidente(
    incidente_id: int,
    session: Session = Depends(get_session)
):
    incidente_existente = session.get(Incidente, incidente_id)

    if not incidente_existente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    # Cambiar el estado a "escalado"
    incidente_existente.estado = "escalado"
    session.add(incidente_existente)
    session.commit()
    session.refresh(incidente_existente)

    return incidente_existente


@router.get("/incidente/radicado/{radicado}", response_model=Incidente)
async def obtener_incidente_por_radicado_endpoint(
    radicado: UUID,
    session: Session = Depends(get_session_replica),
    redis_client: Redis = Depends(get_redis_client)
):
    incidente = obtener_incidente_por_radicado(radicado, session, redis_client)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    return incidente