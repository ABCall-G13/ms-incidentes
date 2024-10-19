from fastapi import APIRouter, Depends, HTTPException
from app.models import Canal, Categoria, Estado, Incidente, Prioridad
from app.database import create_incidente_cache, get_session, get_redis_client, obtener_incidente_cache
from sqlmodel import Session, select
from redis import Redis

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
        return incidente
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    
@router.get("/incidente/{incidente_id}", response_model=Incidente)
async def obtener_incidente(
    incidente_id: int,
    session: Session = Depends(get_session),
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
    session: Session = Depends(get_session)
):
    try:
        # Consulta para obtener todos los incidentes
        statement = select(Incidente)
        results = session.exec(statement).all()  # Ejecutar la consulta
        
        return results  # Devuelve la lista de incidentes
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