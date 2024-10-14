from datetime import datetime
from fastapi import APIRouter, Depends
from app.models import Incidente
from app.database import create_incidente_cache, get_session, get_redis_client
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
    incidente = create_incidente_cache(event_data, session, redis_client)
    return incidente


"""     try:
        incidente = create_incidente_cache(event_data, session, redis_client)
        return incidente
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) """