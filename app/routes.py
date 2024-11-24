from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.cliente_service import verificar_agente_existente, verificar_cliente_existente
from app.models import Canal, Categoria, Estado, Incidente, Prioridad
from app.database import create_incidente_cache, get_session, get_redis_client, obtener_incidente_cache, obtener_incidente_por_radicado, get_session_replica, publish_message, create_problema_comun, obtener_problemas_comunes, ProblemaComun
from sqlmodel import Session, select
from redis import Redis
from typing import List
from app import config
from app.security import ClientToken, get_current_client_token

router = APIRouter()


@router.get("/")
async def health():
    return {"status": "ok"}


@router.post("/incidente", response_model=Incidente) #
async def crear_incidente(
    event_data: Incidente,
    session: Session = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client)
):
    event_data.id = None
    try:
        incidente = create_incidente_cache(event_data, session, redis_client)
        message_data = incidente.model_dump()
        message_data["operation"] = "create"
        publish_message(message_data, config.TOPIC_ID)
        publish_message(message_data, config.NOTIFICATIONS_TOPIC_ID)
        return incidente
    except Exception as e:
        print("Error creating incident:", str(e))
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


@router.get("/incidentes", response_model=list[Incidente])
async def obtener_todos_los_incidentes(
    request: Request,
    session: Session = Depends(get_session_replica),
    client_token: ClientToken = Depends(get_current_client_token)
):
    try:
        print(request.headers)

        try:
            nit_cliente = await verificar_cliente_existente(client_token.email, client_token.token)
            statement = select(Incidente).where(Incidente.cliente_id == nit_cliente)
        except HTTPException as client_exception:
            if client_exception.status_code == 404:
                # Si no es un cliente, intentar verificar si es un agente
                nit_agente = await verificar_agente_existente(client_token.email, client_token.token)
                statement = select(Incidente)
            else:
                raise client_exception

        results = session.exec(statement).all()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al obtener incidentes")


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

    message_data = incidente_existente.model_dump()
    message_data["operation"] = "update"
    publish_message(message_data, config.TOPIC_ID)
    publish_message(message_data, config.NOTIFICATIONS_TOPIC_ID)
    
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

    message_data = incidente_existente.model_dump()
    message_data["operation"] = "update"
    publish_message(message_data, config.TOPIC_ID)

    return incidente_existente


@router.get("/incidente/radicado/{radicado}", response_model=Incidente)
async def obtener_incidente_por_radicado_endpoint(
    radicado: str,
    session: Session = Depends(get_session_replica),
    redis_client: Redis = Depends(get_redis_client)
):
    incidente = obtener_incidente_por_radicado(radicado, session, redis_client)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    return incidente


@router.post("/soluciones", response_model=ProblemaComun)
def registrar_problema_comun(problema: ProblemaComun, session: Session = Depends(get_session)):
    try:
        return create_problema_comun(problema, session)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/soluciones", response_model=List[ProblemaComun])
def listar_problemas_comunes(session: Session = Depends(get_session)):
    try:
        return obtener_problemas_comunes(session)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
        