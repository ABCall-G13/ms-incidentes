# incidentes/test/test_routes.py
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from app.database import get_session_replica
from app.models import Incidente, Categoria, Canal, Estado, Prioridad, ProblemaComun
from uuid import uuid4
from jose import JWTError, jwt

from app.security import ALGORITHM, SECRET_KEY

# Prueba para verificar que la API está funcionando correctamente
def test_health_check(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

# Prueba para crear un incidente
def test_crear_incidente(client, session, incidente):
    # Convert UUID to string for JSON serialization
    incidente_dict = incidente.model_dump()
    incidente_dict["radicado"] = str(incidente_dict["radicado"])

    response = client.post("/incidente", json=incidente_dict)

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert data["cliente_id"] == incidente.cliente_id
    assert data["description"] == incidente.description
    assert data["categoria"] == incidente.categoria.value
    assert "radicado" in data
    assert isinstance(data["radicado"], str)
    
def test_obtener_incidente(client):

    incidente_data = {
        "description": "Test incident",
        "categoria": "acceso",
        "prioridad": "alta",
        "canal": "llamada",
        "cliente_id": 1,
        "estado": "abierto",
        "fecha_creacion": None,
        "fecha_cierre": None,
        "solucion": None,
        "identificacion_usuario": "123456789"
    }
    response = client.post("/incidente", json=incidente_data)

    assert response.status_code == 200
    incidente_creado = response.json()
    incidente_id = incidente_creado["id"]

    response = client.get(f"/incidente/{incidente_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == incidente_id
    assert data["description"] == "Test incident"
    assert data["categoria"] == "acceso"
    assert data["prioridad"] == "alta"
    assert data["canal"] == "llamada"
    assert data["cliente_id"] == 1
    assert data["estado"] == "abierto"
    assert data["fecha_creacion"] == date.today().isoformat()
    assert data["fecha_cierre"] is None
    assert data["solucion"] is None

# Prueba para obtener todos los incidentes
def test_obtener_todos_los_incidentes(client, session, incidente, mocker):
    # Add the incident to the test database
    session.add(incidente)
    session.commit()

    # Create a JWT token with the required claims
    email = "test@example.com"
    token_data = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Mock the 'verificar_cliente_existente' async function
    expected_nit = incidente.cliente_id  # Assuming 'cliente_id' is the NIT
    mock_verificar_cliente = AsyncMock(return_value=expected_nit)
    mocker.patch("app.routes.verificar_cliente_existente", mock_verificar_cliente)

    # Prepare the headers with the Authorization token
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Send the GET request with headers
    response = client.get("/incidentes", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate that the response is a list with at least one incident
    assert isinstance(data, list)
    assert len(data) > 0

    # Validate that the data of the first incident is correct
    incidente_obtenido = data[0]
    assert incidente_obtenido["cliente_id"] == incidente.cliente_id
    assert incidente_obtenido["description"] == incidente.description



def test_obtener_todos_los_incidentes_agente_no_existe(client, mocker):
    # Crear un token de agente inexistente
    email = "agente_inexistente@example.com"
    token_data = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Mock para verificar al agente inexistente
    mock_verificar_agente = AsyncMock(side_effect=HTTPException(status_code=404, detail="Agente no encontrado"))
    mocker.patch("app.routes.verificar_agente_existente", mock_verificar_agente)

    # Headers con el token de autorización
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Enviar solicitud para obtener incidentes
    response = client.get("/incidentes", headers=headers)

    # Validar respuesta de error
    assert response.status_code == 500
    assert response.json()["detail"] == "Error al obtener incidentes"


def test_obtener_valores_permitidos(client):
    response = client.get("/incidentes/fields")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Validar que todas las categorías, prioridades, canales y estados están presentes
    assert "categoria" in data
    assert "prioridad" in data
    assert "canal" in data
    assert "estado" in data

    # Validar que las listas de valores no están vacías
    assert len(data["categoria"]) > 0
    assert len(data["prioridad"]) > 0
    assert len(data["canal"]) > 0
    assert len(data["estado"]) > 0


def test_crear_incidente_error(client, mocker):
    # Mock para forzar un error en la creación del incidente
    mock_create_incidente_cache = mocker.patch("app.routes.create_incidente_cache")
    mock_create_incidente_cache.side_effect = Exception("Error inesperado en la creación del incidente")

    incidente_data = {
        "description": "Test incident",
        "categoria": "acceso",
        "prioridad": "alta",
        "canal": "llamada",
        "cliente_id": 1,
        "estado": "abierto",
        "fecha_creacion": None,
        "fecha_cierre": None,
        "solucion": None,
        "identificacion_usuario": "123456789"
    }

    response = client.post("/incidente", json=incidente_data)
    
    # Validar que el código de error es 500
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Validar el mensaje de error devuelto
    assert response.json()["detail"] == "Error inesperado en la creación del incidente"



# Prueba para solucionar un incidente
def test_solucionar_incidente(client, session, incidente):
    # Agregamos el incidente a la base de datos de prueba
    session.add(incidente)
    session.commit()

    # Preparamos el payload para actualizar la solución
    payload = {"solucion": "Solución al incidente"}

    response = client.put(f"/incidente/{incidente.id}/solucionar", json=payload)
    assert response.status_code == status.HTTP_200_OK

    # Validar que el incidente ahora esté cerrado y tenga la solución correcta
    data = response.json()
    assert data["solucion"] == payload["solucion"]
    assert data["estado"] == Estado.cerrado.value

# Prueba para escalar un incidente
def test_escalar_incidente(client, session, incidente):
    # Agregamos el incidente a la base de datos de prueba
    session.add(incidente)
    session.commit()

    response = client.put(f"/incidente/{incidente.id}/escalar")
    assert response.status_code == status.HTTP_200_OK

    # Validar que el estado del incidente ahora sea "escalado"
    data = response.json()
    assert data["estado"] == Estado.escalado.value
    assert "radicado" in data
    assert isinstance(data["radicado"], str)
    
def test_obtener_incidente_por_radicado(client, session, incidente):
    session.add(incidente)
    session.commit()

    response = client.get(f"/incidente/radicado/{incidente.radicado}")
    assert response.status_code == 200

    data = response.json()
    assert data["cliente_id"] == incidente.cliente_id
    assert data["description"] == incidente.description
    assert data["categoria"] == incidente.categoria.value
    assert data["radicado"] == str(incidente.radicado)

def test_escalar_incidente(client, session):
    # Set up an incident in the database to escalate
    incidente = Incidente(
        cliente_id=123,
        description="Descripción del incidente",
        categoria=Categoria.acceso,
        prioridad=Prioridad.alta,
        canal=Canal.llamada,
        estado=Estado.abierto,
        fecha_creacion=date.today()
    )
    session.add(incidente)
    session.commit()
    session.refresh(incidente)

    # Perform the PUT request to escalate the incident
    response = client.put(f"/incidente/{incidente.id}/escalar")
    assert response.status_code == 200

    # Fetch the escalated incident and validate the state change
    data = response.json()
    assert data["estado"] == Estado.escalado.value
    assert data["id"] == incidente.id
    assert "radicado" in data
    assert isinstance(data["radicado"], str)

    # Ensure the database reflects the escalation
    escalated_incident = session.get(Incidente, incidente.id)
    assert escalated_incident.estado == Estado.escalado

def test_obtener_incidente_not_found(client, mocker):
    # Simulate `None` return for a missing incident
    mocker.patch("app.database.obtener_incidente_cache", return_value=None)

    response = client.get("/incidente/1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Incidente no encontrado"


def test_obtener_todos_los_incidentes_internal_server_error(client, mocker):
    # Create a JWT token with the required claims
    email = "test@example.com"
    token_data = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Mock the 'verificar_cliente_existente' async function
    expected_nit = "some-nit-value"
    mock_verificar_cliente = AsyncMock(return_value=expected_nit)
    mocker.patch("app.routes.verificar_cliente_existente", mock_verificar_cliente)

    # Create a mock session where exec raises an exception
    mock_session = MagicMock()
    mock_session.exec.side_effect = Exception("Database error")

    # Override the 'get_session_replica' dependency to return the mock session
    def mock_get_session_replica():
        yield mock_session

    # Use the 'client' fixture's 'app' attribute to override dependencies
    app = client.app
    app.dependency_overrides[get_session_replica] = mock_get_session_replica

    # Prepare the headers with the Authorization token
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Send the GET request with headers
    response = client.get("/incidentes", headers=headers)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Error al obtener incidentes" in response.json()["detail"]

    # Clean up the dependency override
    app.dependency_overrides.pop(get_session_replica)


def test_obtener_incidente_por_radicado_not_found(client, mocker):
    radicado = uuid4()
    mocker.patch("app.database.obtener_incidente_por_radicado", return_value=None)

    response = client.get(f"/incidente/radicado/{radicado}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Incidente no encontrado"


def test_solucionar_incidente_not_found(client, mocker):
    mocker.patch("sqlmodel.Session.get", return_value=None)

    response = client.put("/incidente/1/solucionar", json={"solucion": "Fixed issue"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Incidente no encontrado"


def test_escalar_incidente_not_found(client, mocker):
    mocker.patch("sqlmodel.Session.get", return_value=None)

    response = client.put("/incidente/1/escalar")
    assert response.status_code == 404
    assert response.json()["detail"] == "Incidente no encontrado"


def test_registrar_problema_comun(client, session):
    problema_data = {
        "description": "Problem description",
        "categoria": Categoria.acceso.value,
        "solucion": "Suggested solution",
        "cliente_id": 1
    }

    response = client.post("/soluciones", json=problema_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["description"] == problema_data["description"]
    assert data["categoria"] == problema_data["categoria"]
    assert data["solucion"] == problema_data["solucion"]

    problema = session.query(ProblemaComun).filter_by(id=data["id"]).first()
    assert problema is not None
    assert problema.description == problema_data["description"]
    assert problema.categoria == Categoria(problema_data["categoria"])
    assert problema.solucion == problema_data["solucion"]


def test_listar_problemas_comunes(client, session):
    problema = ProblemaComun(
        description="Sample problem",
        categoria=Categoria.funcionamiento,
        solucion="Sample solution",
        cliente_id = 1
    )
    session.add(problema)
    session.commit()

    response = client.get("/soluciones")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    found = any(item["id"] == problema.id for item in data)
    assert found


def test_registrar_problema_comun_value_error(client, mocker):
    problema_data = {
        "description": "Problem description",
        "categoria": "acceso",
        "solucion": "Suggested solution"
    }

    mocker.patch("app.routes.create_problema_comun", side_effect=ValueError("Test error"))

    response = client.post("/soluciones", json=problema_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Test error"}


def test_listar_problemas_comunes_value_error(client, mocker):
    mocker.patch("app.routes.obtener_problemas_comunes", side_effect=ValueError("Test error"))

    response = client.get("/soluciones")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Test error"}