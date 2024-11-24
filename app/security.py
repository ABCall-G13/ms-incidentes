from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.database import get_session
from app import config

SECRET_KEY = config.SECRET_KEY
ALGORITHM = "HS256"

class ClientToken:
    def __init__(self, email: str, token: str):
        self.email = email
        self.token = token

def get_current_client_token(request: Request, db: Session = Depends(get_session)) -> ClientToken:

    print("get_current_client_token", request.headers)
    credentials_exception = HTTPException(
        status_code=401,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = request.headers.get("X-Forwarded-Authorization") or request.headers.get("Authorization")
    
    if not token or not token.startswith("Bearer "):
        raise credentials_exception
    
    token = token[7:]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    return ClientToken(email=email, token=token)