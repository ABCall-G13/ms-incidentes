from app.database import get_engine, init_db, get_redis_client, get_session_replica
from app.models import Incidente, Categoria, Canal, Prioridad, Estado
from sqlmodel import Session, SQLModel
import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from main import app
from uuid import uuid4

# Establish engines at module level for reuse
engine = get_engine("sqlite:///:memory:?check_same_thread=False")
engine_replica = get_engine("sqlite:///:memory:?check_same_thread=False")

# Initialize tables once for both engines
init_db(engine, engine_replica)

@pytest.fixture(scope="module")
def session():
    with Session(engine) as session:
        yield session

@pytest.fixture(scope="module")
def session_replica():
    with Session(engine_replica) as session:
        yield session

@pytest.fixture(name="redis_client")
def redis_client_fixture():
    return FakeRedis()

@pytest.fixture(name="client")
def client_fixture(session: Session, session_replica: Session, redis_client: FakeRedis):
    def _get_test_session():
        yield session

    def _get_test_session_replica():
        yield session_replica

    def _get_test_redis_client():
        return redis_client

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_session_replica] = _get_test_session_replica
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
        categoria=Categoria.acceso,
        prioridad=Prioridad.alta,
        canal=Canal.llamada,
        estado=Estado.abierto,
        fecha_creacion=None,
        fecha_cierre=None,
        solucion=None,
        radicado=uuid4()
    )
