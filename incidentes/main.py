
from fastapi import FastAPI
from app.routes import router as incidente_router

app = FastAPI()

app.include_router(incidente_router)

