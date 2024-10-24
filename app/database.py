# incidentes/app/database.py
import json
from typing import Generator, Optional
from redis import Redis
from sqlmodel import Session, create_engine, SQLModel
from app import config
from app.models import Incidente
from uuid import UUID, uuid4


def get_engine(database_url: Optional[str] = None):
    if database_url:
        return create_engine(database_url, echo=True)
    if config.DB_SOCKET_PATH_PRIMARY:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@/{config.DB_NAME}?unix_socket={config.DB_SOCKET_PATH_PRIMARY}"
    else:
        database_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(database_url, echo=True)


engine = get_engine()


def init_db(engine):
    SQLModel.metadata.create_all(engine)


redis_client = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_redis_client() -> Redis:
    return redis_client


def create_incidente_cache(incidente: Incidente, session: Session, redis_client: Redis):
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
    
    