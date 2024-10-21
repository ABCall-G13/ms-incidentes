# incidentes/app/database.py
import json
from typing import Generator, Optional
from redis import Redis
from sqlmodel import Session, create_engine, SQLModel
from app import config
from app.models import Incidente
from google.cloud import pubsub_v1


def get_engine(database_url: Optional[str] = None):
    if database_url:
        return create_engine(database_url, echo=True)
    if config.DB_SOCKET_PATH_PRIMARY:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@/{
            config.DB_NAME}?unix_socket={config.DB_SOCKET_PATH_PRIMARY}"
    else:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{
            config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"

    if config.DB_SOCKET_PATH_REPLICA:
        database_url = f"mysql+mysqlconnector://{config.DB_USER_REPLICA}:{config.DB_PASSWORD_REPLICA}@/{
            config.DB_NAME_REPLICA}?unix_socket={config.DB_SOCKET_PATH_REPLICA}"
    else:
        database_url = f"mysql+mysqlconnector://{config.DB_USER_REPLICA}:{config.DB_PASSWORD_REPLICA}@{
            config.DB_HOST_REPLICA}:{config.DB_PORT_REPLICA}/{config.DB_NAME_REPLICA}"
    return create_engine(database_url, echo=True)


engine = get_engine()


def init_db(engine):
    SQLModel.metadata.create_all(engine)


publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(config.PROJECT_ID, config.TOPIC_ID)
redis_client = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_redis_client() -> Redis:
    return redis_client


def create_incidente_cache(incidente: Incidente, session: Session, redis_client: Redis):
    try:
        session.add(incidente)
        session.commit()
        session.refresh(incidente)
        incidente_json = incidente.model_dump_json()
        redis_client.set(f"incidente:{incidente.id}", incidente_json)
        return incidente
    except Exception as e:
        session.rollback()
        raise Exception(f"Error al crear incidente: {str(e)}")
    finally:
        session.close()


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