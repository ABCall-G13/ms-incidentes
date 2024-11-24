import pytest
import httpx
from httpx import Response
from app.external_services import registrar_incidente_facturado

@pytest.mark.asyncio
async def test_registrar_incidente_facturado(mocker):
    # Datos de prueba
    radicado_incidente = "12345"
    costo = 100.0
    fecha_incidente = "2023-10-01"
    nit = "123456789"

    # Mock de la respuesta de httpx
    mock_response = mocker.Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": "Incidente registrado con éxito"
    }

    # Mock del cliente HTTP
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    # Llamada a la función a probar
    response = await registrar_incidente_facturado(radicado_incidente, costo, fecha_incidente, nit)

    # Validaciones
    assert response == {"message": "Incidente registrado con éxito"}
    httpx.AsyncClient.post.assert_called_once_with(
        "https://ms-facturacion-345518488840.us-central1.run.app/incidentes",
        json={
            "radicado_incidente": radicado_incidente,
            "costo": costo,
            "fecha_incidente": fecha_incidente,
            "nit": nit
        },
        timeout=10.0
    )