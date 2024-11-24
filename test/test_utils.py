import pytest
from app.utils import determinar_origen_cambio


def test_determinar_origen_cambio_postman():
    headers = {"User-Agent": "PostmanRuntime/7.26.8"}
    assert determinar_origen_cambio(headers) == "Postman"


def test_determinar_origen_cambio_frontend():
    headers = {"User-Agent": "Mozilla/5.0"}
    assert determinar_origen_cambio(headers) == "Frontend"


def test_determinar_origen_cambio_otro():
    headers = {"User-Agent": "CustomAgent/1.0"}
    assert determinar_origen_cambio(headers) == "Otro"
