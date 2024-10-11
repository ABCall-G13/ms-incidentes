import json
from typing import List
from redis import Redis
from sqlmodel import Session, create_engine, SQLModel, text
from app import config
from app.models import Incidente
from google.cloud import pubsub_v1

# URL para la base de datos primaria
if config.DB_SOCKET_PATH_PRIMARY:
    SQLALCHEMY_DATABASE_URL_PRIMARY = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@/{config.DB_NAME}?unix_socket={config.DB_SOCKET_PATH_PRIMARY}"
else:
    SQLALCHEMY_DATABASE_URL_PRIMARY = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"


engine_primary = create_engine(SQLALCHEMY_DATABASE_URL_PRIMARY)

# Crear las tablas en la base de datos primaria
SQLModel.metadata.create_all(engine_primary)

# Instancia redis
redis_client = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

def create_session():
    return Session(engine_primary)

def store_and_refresh(incidente, session):
    session.add(incidente)
    session.commit()
    session.refresh(incidente)

def save_incident_to_redis(incidente):
    incidente_id = incidente.id
    incidente_json = json.dumps({
        "id": incidente.id,
        "cliente_id": incidente.cliente_id,
        "description": incidente.description,
        "categoria": incidente.categoria,
        "prioridad": incidente.prioridad,
        "canal": incidente.canal
    })
    redis_client.set(f"incidentes:{incidente_id}", incidente_json)
    print(f"Incidente {incidente_id} guardado en Redis.")

def create_incidente_cache(incidente: Incidente):
    session = create_session()
    try:
        store_and_refresh(incidente, session)
        save_incident_to_redis(incidente)
    except Exception as e:
        session.rollback()
        print(f"Error al crear incidente: {e}")
        raise
    finally:
        session.close()
    return incidente

def obtener_incidentes_cache() -> List[Incidente]:
    keys = redis_client.keys("incidentes:*")
    incidentes = []
    for key in keys:
        incidente_json = redis_client.get(key)
        incidente_dict = json.loads(incidente_json)
        incidente = Incidente(**incidente_dict)
        incidentes.append(incidente)
    return incidentes

def obtener_incidentes_cache() -> List[Incidente]:
    keys = redis_client.keys("incidentes:*")
    incidentes = []
    for key in keys:
        incidente_json = redis_client.get(key)
        incidente_dict = json.loads(incidente_json)
        incidente = Incidente(**incidente_dict)
        incidentes.append(incidente)
    return incidentes
