import pytest
from unittest.mock import MagicMock
from datetime import date, datetime
from app.models import Incidente, LogIncidente, Estado
from app.database import actualizar_incidente, registrar_log_incidente, obtener_logs_por_incidente


@pytest.fixture
def session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.exec = MagicMock()
    return session


@pytest.fixture
def incidente():
    return Incidente(
        id=1,
        cliente_id=123,
        description="Descripción del incidente",
        categoria="acceso",
        prioridad="alta",
        canal="llamada",
        estado=Estado.abierto,
        fecha_creacion=date.today(),
        fecha_cierre=None,
        solucion=None,
        radicado="ABC12345"
    )


@pytest.fixture
def event_data():
    class EventData:
        solucion = "Solución al problema"
    return EventData()


def test_actualizar_incidente(session, incidente, event_data):
    result = actualizar_incidente(incidente, event_data, session)
    assert result.solucion == event_data.solucion
    assert result.estado == Estado.cerrado
    assert result.fecha_cierre == date.today()
    session.add.assert_called_once_with(incidente)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(incidente)


def test_registrar_log_incidente(session, incidente):
    origen_cambio = "Postman"
    registrar_log_incidente(incidente, origen_cambio, session)
    log = session.add.call_args[0][0]
    assert log.incidente_id == incidente.id
    assert log.cuerpo_completo == incidente.model_dump_json()
    assert log.origen_cambio == origen_cambio
    session.commit.assert_called_once()


def test_obtener_logs_por_incidente(session):
    incidente_id = 1
    log1 = LogIncidente(id=1, incidente_id=incidente_id, cuerpo_completo="{}",
                        fecha_cambio=datetime.utcnow(), origen_cambio="Postman")
    log2 = LogIncidente(id=2, incidente_id=incidente_id, cuerpo_completo="{}",
                        fecha_cambio=datetime.utcnow(), origen_cambio="Frontend")
    session.exec.return_value.all.return_value = [log1, log2]
    logs = obtener_logs_por_incidente(incidente_id, session)
    assert len(logs) == 2
    assert logs[0].id == log1.id
    assert logs[1].id == log2.id
    session.exec.assert_called_once()
