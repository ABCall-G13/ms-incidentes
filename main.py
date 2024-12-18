import os
from fastapi import FastAPI
from app.routes import router as incidente_router
# Importa la función init_db y el engine
from app.database import init_db, engine, engine_replica
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("TESTING") != "True":
        init_db(engine, engine_replica)  # Inicializa la base de datos y crea las tablas
    yield
    # Este código se ejecuta cuando la aplicación se apaga

# Inicializa la aplicación FastAPI usando lifespan
app = FastAPI(lifespan=lifespan)

# Incluir el router
app.include_router(incidente_router)

app.include_router(incidente_router)

app.add_middleware(
    CORSMiddleware,
    # Permite todos los orígenes, puedes restringirlo a ciertos dominios en producción
    allow_origins=["*"],
    allow_credentials=True,
    # Permite todos los métodos (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_methods=["*"],
    allow_headers=["*"],  # Permite todos los encabezados
)
