
from datetime import date
from fastapi.testclient import TestClient

from app.models import Incidente


def test_crear_incidente(client: TestClient):
    incidente_data = {
        # "id": 1,  # No es necesario proporcionar 'id' ya que se genera automáticamente
        "description": "Test incident",
        "categoria": "acceso",
        "prioridad": "alta",
        "canal": "llamada",
        "cliente_id": 1,
        "estado": "abierto",
        "fecha_creacion": None,
        "fecha_cierre": None,  # Incluir campos opcionales si son necesarios
        "solucion": None
    }
    response = client.post("/incidente", json=incidente_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["description"] == "Test incident"
    assert data["categoria"] == "acceso"
    assert data["prioridad"] == "alta"
    assert data["canal"] == "llamada"
    assert data["cliente_id"] == 1
    assert data["estado"] == "abierto"
    assert data["fecha_creacion"] == date.today().isoformat()
    assert data["fecha_cierre"] is None
    assert data["solucion"] is None
    
def test_obtener_incidente(client: TestClient, incidente: Incidente):
 
    incidente_data = {
        "description": "Test incident",
        "categoria": "acceso",
        "prioridad": "alta",
        "canal": "llamada",
        "cliente_id": 1,
        "estado": "abierto",
        "fecha_creacion": None,
        "fecha_cierre": None,  
        "solucion": None
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