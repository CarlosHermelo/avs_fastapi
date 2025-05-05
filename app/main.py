# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api import endpoints

app = FastAPI(title="PAMI SIMAP API con Qdrant",
              description="API para consultas a la base de datos vectorial Qdrant",
              version="1.0.0")

# Configurar CORS para permitir solicitudes desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las origins en desarrollo
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los headers
)

# Montar los endpoints de la API
app.include_router(endpoints.router)

# Montar el directorio de archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def read_root():
    return {"message": "API de PAMI con Qdrant funcionando. Use /docs para ver la documentación."}

@app.get("/consulta")
async def serve_consulta_page():
    """Sirve la página de consulta Qdrant HTML"""
    return FileResponse("app/static/consulta_qdrant.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

