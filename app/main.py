# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints

app = FastAPI()

# Configurar CORS para permitir solicitudes desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las origins en desarrollo
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los headers
)

app.include_router(endpoints.router)

