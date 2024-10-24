# incidentes/test/conftest.py
from datetime import date
import os
import pytest
from sqlmodel import Session
from app.database import get_engine, get_session, get_redis_client, init_db
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from app.models import Incidente, Categoria, Canal, Prioridad, Estado
from main import app
from uuid import uuid4

# Establece la variable de entorno para indicar que estamos en pruebas
os.environ["TESTING"] = "True"

# Fixture para la sesión de la base de datos
@pytest.fixture(name="session")
def session_fixture():
    engine = get_engine("sqlite:///test_database.db")
    init_db(engine)
    
    with Session(engine) as session:
        yield session
    engine.dispose()
    # Eliminar la base de datos de prueba al final de las pruebas
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")

# Fixture para el cliente de Redis falso (usado para cache simulado)
@pytest.fixture(name="redis_client")
def redis_client_fixture():
    return FakeRedis()

# Fixture para el cliente de pruebas FastAPI
@pytest.fixture(name="client")
def client_fixture(session: Session, redis_client: FakeRedis):
    # Sobrescribe la dependencia de la sesión con la sesión de prueba
    def _get_test_session():
        yield session

    # Sobrescribe la dependencia del cliente Redis con el cliente simulado
    def _get_test_redis_client():
        return redis_client

    # Aplicar las dependencias sobrescritas
    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_redis_client] = _get_test_redis_client

    # Utiliza el cliente de pruebas para hacer solicitudes a la API
    with TestClient(app) as client:
        yield client

    # Limpia las dependencias sobrescritas después de las pruebas
    app.dependency_overrides.clear()

# Fixture para crear un objeto de incidente de ejemplo
@pytest.fixture
def incidente():
    return Incidente(
        id=1,
        cliente_id=123,
        description="Descripción del incidente",
        categoria=Categoria.acceso,
        prioridad=Prioridad.alta,
        canal=Canal.llamada,
        estado=Estado.abierto,
        fecha_creacion=None,
        fecha_cierre=None,
        solucion=None,
        radicado=uuid4()
    )
