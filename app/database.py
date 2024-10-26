# incidentes/app/database.py
import json
from typing import Generator, Optional
from redis import Redis
from sqlmodel import Session, create_engine, SQLModel
from app import config
from app.models import Incidente
from uuid import UUID, uuid4
from google.cloud import pubsub_v1
from google.oauth2 import service_account
import os
from datetime import date, datetime

def get_engine(database_url: Optional[str] = None):
    if database_url:
        return create_engine(database_url, echo=True)
    if config.DB_SOCKET_PATH_PRIMARY:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@/{config.DB_NAME}?unix_socket={config.DB_SOCKET_PATH_PRIMARY}"
    else:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(database_url, echo=True)


def get_engine_replica(database_url: Optional[str] = None):
    if database_url:
        return create_engine(database_url, echo=True)
    if config.DB_SOCKET_PATH_REPLICA:
        database_url = f"mysql+mysqlconnector://{config.DB_USER_REPLICA}:{config.DB_PASSWORD_REPLICA}@/{config.DB_NAME_REPLICA}?unix_socket={config.DB_SOCKET_PATH_REPLICA}"
    else:
        database_url = f"mysql+mysqlconnector://{config.DB_USER_REPLICA}:{config.DB_PASSWORD_REPLICA}@{config.DB_HOST_REPLICA}:{config.DB_PORT_REPLICA}/{config.DB_NAME_REPLICA}"
    
    return create_engine(database_url, echo=True)


engine = get_engine()
engine_replica = get_engine_replica()


def init_db(engine, engine_replica):
    SQLModel.metadata.create_all(engine)
    SQLModel.metadata.create_all(engine_replica)

redis_client = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_session_replica() -> Generator[Session, None, None]:
    with Session(engine_replica) as session:
        yield session


def get_redis_client() -> Redis:
    return redis_client


def create_incidente_cache(incidente: Incidente, session: Session, redis_client: Redis):
    session_replica = None
    try:
        if not incidente.radicado:
            incidente.radicado = uuid4()
        session.add(incidente)
        session.commit()
        session.refresh(incidente)

        incidente_json = incidente.model_dump_json()
        redis_client.set(f"incidente:{incidente.id}", incidente_json)
        return incidente
    except Exception as e:
        session.rollback()
        if session_replica:
            session_replica.rollback()
        raise Exception(f"Error al crear incidente: {str(e)}")
    finally:
        session.close()
        if session_replica:
            session_replica.close()


def obtener_incidente_cache(incidente_id, session, redis_client):
    incidente = redis_client.get(f"incidente:{incidente_id}")
    if incidente:
        return json.loads(incidente)
    else:
        incidente = session.get(Incidente, incidente_id)
        if incidente:
            incidente_json = incidente.model_dump_json()
            redis_client.set(f"incidente:{incidente_id}", incidente_json)
            return incidente_json
        return None


def obtener_incidente_por_radicado(radicado: UUID, session: Session, redis_client: Redis):
    incidente = redis_client.get(f"incidente:radicado:{radicado}")
    
    if incidente:
        incidente_data = json.loads(incidente)
        return Incidente(**incidente_data) 
    
    else:
        incidente = session.query(Incidente).filter_by(radicado=radicado).first()
        
        if incidente:
            incidente_json = incidente.model_dump_json()
            redis_client.set(f"incidente:radicado:{radicado}", incidente_json)
            return incidente
        return None
    

def custom_serializer(obj): #
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def publish_message(data):
    if not config.is_testing():
        credentials = service_account.Credentials.from_service_account_file(config.GOOGLE_APPLICATION_CREDENTIALS)
        publisher = pubsub_v1.PublisherClient(credentials=credentials)
        topic_path = publisher.topic_path(config.PROJECT_ID, config.TOPIC_ID)
        message_data = json.dumps(data, default=custom_serializer).encode("utf-8")
        publisher.publish(topic_path, message_data)
    