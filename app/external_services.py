import httpx

async def registrar_incidente_facturado(radicado_incidente: str, costo: float, fecha_incidente: str, nit: str):
    url = "https://ms-facturacion-345518488840.us-central1.run.app/incidentes"
    payload = {
        "radicado_incidente": radicado_incidente,
        "costo": costo,
        "fecha_incidente": fecha_incidente,
        "nit": nit
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload,  timeout=10.0)
        if response.status_code != 200:
            raise Exception(f"Error al registrar incidente facturado: {response.text}")
        return response.json()