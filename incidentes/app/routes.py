from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models import Incidente
from app.database import create_incidente_cache, get_session, get_redis_client, obtener_incidente_cache
from sqlmodel import Session
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