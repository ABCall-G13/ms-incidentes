# incidentes/test/conftest.py
from datetime import date
import os
import pytest
from sqlmodel import create_engine, SQLModel, Session
from app.database import get_session, get_redis_client, get_engine, init_db
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from app.models import Canal, Categoria, Estado, Incidente, Prioridad
from main import app

@pytest.fixture(name="session")
def session_fixture():
    engine = get_engine("sqlite:///test_database.db")
    init_db(engine)
    with Session(engine) as session:
        yield session
    
    engine.dispose()    
    # Clean up the database file after tests
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")

@pytest.fixture(name="redis_client")
def redis_client_fixture():
    return FakeRedis()

@pytest.fixture(name="client")
def client_fixture(session: Session, redis_client: FakeRedis):
    def _get_test_session():
        yield session

    def _get_test_redis_client():
        return redis_client

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_redis_client] = _get_test_redis_client

    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()
    
@pytest.fixture
def incidente():
    return Incidente(
        id=1,
        cliente_id=123,
        description="Descripción del incidente",
        categoria=Categoria.acceso,     # Usa el miembro del Enum
        prioridad=Prioridad.alta,       # Usa el miembro del Enum
        canal=Canal.llamada,            # Usa el miembro del Enum
        estado=Estado.abierto,          # Usa el miembro del Enum
        fecha_creacion=date.today(),    # Usa un objeto date, no una cadena
        fecha_cierre=None,
        solucion=None
    )