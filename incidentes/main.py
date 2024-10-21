
from fastapi import FastAPI
from app.routes import router as incidente_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(incidente_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes, puedes restringirlo a ciertos dominios en producción
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

