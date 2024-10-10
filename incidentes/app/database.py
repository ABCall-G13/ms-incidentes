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

# URL para la base de datos réplica
if config.DB_SOCKET_PATH_REPLICA:
    SQLALCHEMY_DATABASE_URL_REPLICA = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@/{config.DB_NAME}?unix_socket={config.DB_SOCKET_PATH_REPLICA}"
else:
    SQLALCHEMY_DATABASE_URL_REPLICA = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST_REPLICA}:{config.DB_PORT}/{config.DB_NAME_REPLICA}"

# Crear motores para las dos bases de datos
engine_primary = create_engine(SQLALCHEMY_DATABASE_URL_PRIMARY)
engine_replica = create_engine(SQLALCHEMY_DATABASE_URL_REPLICA)

# Inica Pub/Sub Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(config.PROJECT_ID, config.TOPIC_ID)

# Crear las tablas en la base de datos primaria
SQLModel.metadata.create_all(engine_primary)


# Instancia redis
redis_client = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

def create_session(primary: bool = True):
    """Crea una sesión, usa la primaria si primary=True, de lo contrario usa la réplica."""
    if primary:
        session = Session(engine_primary)
    else:
        session = Session(engine_replica)
    return session

def create_incidente(incidente: Incidente):
    """Crea un incidente en la base de datos primaria."""
    incidente.id = None
    session = create_session(primary=True)  # Siempre en la primaria
    session.add(incidente)
    session.commit()
    session.refresh(incidente)
    session.close()
    return incidente

def create_incidente_cache(incidente: Incidente):
    """Crea un incidente en la base de datos primaria."""
    session = create_session(primary=True)  # Siempre en la primaria
    
    try:
        
        session.add(incidente)
        session.commit()
        session.refresh(incidente)
        
        # Guardar el incidente en el cache Redis
        incidente_id = incidente.id
        incidente_json = json.dumps({
            "id": incidente.id,
            "user_id": incidente.user_id,
            "descripcion": incidente.description,
        })
        
        
        # Guardar en Redis con una clave basada en el ID del incidente
        redis_client.set(f"incidentes:{incidente_id}", incidente_json)

        print(f"Incidente {incidente_id} guardado en Redis.")
        

    except Exception as e:
        session.rollback()
        print(f"Error al crear incidente: {e}")
        raise
    finally:
        session.close()

    return incidente


def obtener_incidentes_primaria():
    """Obtiene todos los incidentes desde la base de datos réplica."""
    session = create_session(primary=True)  # Para Consultas desde la réplica cambiarle el valor a false
    incidentes = session.query(Incidente).all()
    session.close()
    return incidentes

def obtener_incidentes_replica():
    """Obtiene todos los incidentes desde la base de datos réplica."""
    session = create_session(primary=False)  # Para Consultas desde la réplica cambiarle el valor a false
    incidentes = session.query(Incidente).all()
    session.close()
    return incidentes


def obtener_incidentes_cache() -> List[Incidente]:
    """Obtiene todos los incidentes desde Redis o la base de datos réplica."""
    
    # Intentar obtener los incidentes del caché
    keys = redis_client.keys("incidentes:*")
    
    if keys:
        print("Incidentes obtenidos desde el caché.")
        incidentes = []
        for key in keys:
            incidente_json = redis_client.get(key)
            if incidente_json:
                incidentes.append(Incidente(**json.loads(incidente_json)))
        return incidentes

    # Si no están en el caché, consultar la base de datos
    print("Incidentes no encontrados en caché, consultando la base de datos...")
    session = create_session(primary=True)
    incidentes = session.query(Incidente).all()
    session.close()

    # Guardar cada incidente individualmente en el caché
    for incidente in incidentes:
        incidente_json = json.dumps(incidente.dict())
        redis_client.set(f"incidentes:{incidente.id}", incidente_json)

    return incidentes




def obtener_incidentes_user(user_id: int):
    """Obtiene todos los incidentes de un usuario desde la réplica."""
    session = create_session(primary=False)# Para Consultas desde la réplica cambiarle el valor a false
    incidentes = session.query(Incidente).filter(Incidente.user_id == user_id).all()
    session.close()
    return incidentes



def obtener_incidentes_user_cache(user_id: int):
 
    # Buscar todas las claves que correspondan a incidentes en Redis
    keys = redis_client.keys("incidentes:*")
    
    incidentes = []
    
    # Recorrer las claves y filtrar por user_id
    for key in keys:
        incidente_json = redis_client.get(key)
        if incidente_json:
            incidente_data = json.loads(incidente_json)
            
            # Si el incidente pertenece al user_id especificado, lo añadimos a la lista
            if incidente_data["user_id"] == user_id:
                incidentes.append(incidente_data)
    
    # Si encontramos incidentes en caché, retornarlos
    if incidentes:
        print("Incidentes obtenidos desde la caché.")
        return incidentes
    
    # Si no hay incidentes en caché, buscar en la base de datos
    print("Incidentes no encontrados en caché, consultando la base de datos...")
    incidentes_db = obtener_incidentes_user(user_id)
    
    # Si encontramos incidentes en la base de datos, guardarlos en Redis y devolverlos
    if incidentes_db:
        for incidente in incidentes_db:
            incidente_json = json.dumps(incidente.dict())
            redis_client.set(f"incidentes:{incidente.id}", incidente_json)
        
        print("Incidentes guardados en caché.")
        return incidentes_db

    # Si no se encuentran incidentes ni en caché ni en la base de datos
    return []


def borrar_primaria():
    session = create_session(primary=True)
    sql_query = text("truncate table incidente")
    session.execute(sql_query)
    session.commit()
    session.close()
    

def borrar_replica():
    session = create_session(primary=False)
    sql_query = text("truncate table incidente")
    session.execute(sql_query)
    session.commit()
    session.close()
    
def borrar_cache():
    redis_client.flushdb()