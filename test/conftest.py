# incidentes/test/conftest.py
from datetime import date
import os
import pytest
from sqlmodel import Session
from app.database import get_engine, get_session, get_redis_client, init_db, get_session_replica, get_engine_replica
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from app.models import Incidente, Categoria, Canal, Prioridad, Estado
from main import app
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
# Establece la variable de entorno para indicar que estamos en pruebas
os.environ["TESTING"] = "True"

# Fixture para la sesión de la base de datos
@pytest.fixture(name="session")
def session_fixture():
    # Create engines for SQLite in-memory databases
    engine = get_engine("sqlite:///test_database.db")
    engine_replica = get_engine_replica("sqlite:///test_database.db")
    
    # Initialize the databases immediately to ensure schema is created
    init_db(engine, engine_replica)
    
    with Session(engine) as session:
        yield session

    # Dispose of the engines
    engine.dispose()
    engine_replica.dispose()
    
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")

# Fixture para el cliente de Redis falso (usado para cache simulado)
@pytest.fixture(name="redis_client")
def redis_client_fixture():
    return FakeRedis()

# Fixture para el cliente de pruebas FastAPI
@pytest.fixture(name="client")
def client_fixture(session: Session, redis_client: FakeRedis):
    # Override the session dependency to use the test session
    def _get_test_session():
        yield session

    # Override the replica session to also use the primary test session for simplicity
    def _get_test_session_replica():
        yield session 

    # Override the Redis client dependency
    def _get_test_redis_client():
        return redis_client

    # Apply dependency overrides
    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_session_replica] = _get_test_session_replica  # Ensure this is overridden for tests
    app.dependency_overrides[get_redis_client] = _get_test_redis_client

    # Use the TestClient to make API requests
    with TestClient(app) as client:
        yield client

    # Clear overrides after tests
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
        radicado=str(uuid4())[:8]
    )
