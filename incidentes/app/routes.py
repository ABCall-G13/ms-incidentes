import json
from fastapi import APIRouter, HTTPException
from app.models import Incidente
from app.database import borrar_cache, borrar_primaria, borrar_replica, create_incidente, obtener_incidentes_cache, create_incidente_cache, obtener_incidentes_primaria, obtener_incidentes_replica, obtener_incidentes_user, publisher, topic_path


router = APIRouter()

@router.get("/")
async def health():
    return {"status": "ok"}


@router.post("/incidente")
async def crear_incidente(event_data: Incidente):
    print(event_data)
    incidente = create_incidente(event_data)
    message_data = event_data.dict()
    try:
        future = publisher.publish(topic_path, json.dumps(message_data).encode("utf-8"))
        message_id = future.result()
        return {"incidente": incidente, "message_id": message_id}
    
    except Exception as e:
        print(f"Failed to publish message to Pub/Sub: {e}")
        
        raise HTTPException(status_code=500, detail="Incident created, but failed to publish message to Pub/Sub.")
    

@router.post("/incidente_cache")
async def crear_incidente_cache(event_data: Incidente ):
    event_data.id = None
    incidente = create_incidente_cache(event_data)
    return incidente



@router.get("/incidentes_primaria")
async def obtener_todos():
    incidentes = obtener_incidentes_primaria()
    return incidentes

@router.get("/incidentes_replica")
async def obtener_todos():
    incidentes = obtener_incidentes_replica()
    return incidentes

@router.get("/incidentes_cache")
async def obtener_todos_cache():
    incidentes =  obtener_incidentes_cache()
    return incidentes



@router.get("/incidentes/{user_id}")
async def obtener_incidentes_por_usuario(user_id: int):
    incidentes = obtener_incidentes_user(user_id)
    return incidentes

@router.get("/incidentes_Cache/{user_id}")
async def obtener_incidentes_por_usuario_cache(user_id: int):
    incidentes = obtener_incidentes_user(user_id)
    return incidentes


@router.get("/borrar_primaria")
async def get_borrar_primaria():
    borrar_primaria()
    return "Se eliminaron los registros de la base de datos primaria"

@router.get("/borrar_replica")
async def get_borrar_replica():
    borrar_replica()
    return "Se eliminaron los registros de la base de datos replica"
    
    
@router.get("/borrar_cache")
async def get_borrar_redis():
    borrar_cache()
    return "Se eliminaron los registros de la memoria cache"


