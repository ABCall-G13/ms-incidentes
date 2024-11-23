# FILE: tests/unit/test_security.py
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt
from app import config
from app.security import get_current_client_token

SECRET_KEY = config.SECRET_KEY
ALGORITHM = "HS256"

# Mock database dependency
@pytest.fixture
def db():
    return Session()

# Mock request with headers
@pytest.fixture
def request_with_valid_token():
    token = jwt.encode({"sub": "test@example.com"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def request_with_invalid_token():
    return {"Authorization": "Bearer invalidtoken"}

@pytest.fixture
def request_without_token():
    return {}

def test_get_current_email_valid_token(request_with_valid_token, db):
    request = type('Request', (object,), {"headers": request_with_valid_token})
    user_token = get_current_client_token(request, db)
    assert user_token.email == "test@example.com"
    assert user_token.token is not None

def test_get_current_email_invalid_token(request_with_invalid_token, db):
    request = type('Request', (object,), {"headers": request_with_invalid_token})
    with pytest.raises(HTTPException) as excinfo:
        get_current_client_token(request, db)
    assert excinfo.value.status_code == 401

def test_get_current_email_without_token(request_without_token, db):
    request = type('Request', (object,), {"headers": request_without_token})
    with pytest.raises(HTTPException) as excinfo:
        get_current_client_token(request, db)
    assert excinfo.value.status_code == 401