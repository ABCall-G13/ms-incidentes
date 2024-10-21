# incidentes/test/test_routes.py
from datetime import date
from fastapi import status
from app.models import Incidente, Estado

# Prueba para verificar que la API está funcionando correctamente
def test_health_check(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

# Prueba para crear un incidente
def test_crear_incidente(client, session, incidente):
    # Preparamos el payload del incidente a enviar en el POST
  

    response = client.post("/incidente", json=incidente.model_dump())

    # Verifica el código de estado y luego revisa la estructura JSON
    assert response.status_code == 200  # Asegúrate de que el código de estado sea 200

    data = response.json()  # Obtén la respuesta en formato JSON
    
    # Validamos que los datos recibidos sean consistentes
    assert isinstance(data, dict)  # Verifica que la respuesta sea un diccionario
    assert data["cliente_id"] == incidente.cliente_id
    assert data["description"] == incidente.description
    assert data["categoria"] == incidente.categoria.value
    
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

# Prueba para obtener todos los incidentes
def test_obtener_todos_los_incidentes(client, session, incidente):
    # Agregamos el incidente a la base de datos de prueba
    session.add(incidente)
    session.commit()

    response = client.get("/incidentes")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validar que la respuesta sea una lista con al menos un incidente
    assert isinstance(data, list)
    assert len(data) > 0

    # Validar que los datos del primer incidente sean correctos
    incidente_obtenido = data[0]
    assert incidente_obtenido["cliente_id"] == incidente.cliente_id
    assert incidente_obtenido["description"] == incidente.description

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
