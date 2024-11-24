def determinar_origen_cambio(headers):
    user_agent = headers.get("User-Agent", "Desconocido")
    if "PostmanRuntime" in user_agent:
        return "Postman"
    elif "Mozilla" in user_agent:
        return "Frontend"
    else:
        return "Otro"