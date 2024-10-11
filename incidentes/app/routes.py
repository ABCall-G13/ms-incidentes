import json
from fastapi import APIRouter, HTTPException
from app.models import Incidente
from app.database import create_incidente_cache

router = APIRouter()

@router.get("/")
async def health():
    return {"status": "ok"}


@router.post("/incidente", response_model=Incidente)
async def crear_incidente(event_data: Incidente):
    event_data.id = None
    incidente = create_incidente_cache(event_data)
    return incidente

@router.get("/incidentes", response_model=list[Incidente])
async def obtener_incidentes():
    incidentes = obtener_incidentes_cache()
    return incidentes

    

