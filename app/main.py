# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api import endpoints
from app.core.logging_config import get_logger
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store, get_llm

# Obtener el logger
logger = get_logger()

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

# Inicializar recursos al arranque de la aplicación
@app.on_event("startup")
async def startup_event():
    logger.info("Inicializando recursos de la aplicación...")
    # Inicializar los recursos singleton
    get_embeddings()
    get_qdrant_client()
    get_vector_store()
    get_llm()
    logger.info("Recursos inicializados correctamente")

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

@app.get("/frontend-client")
async def serve_frontend_client():
    """Sirve la página frontend_client.html"""
    return FileResponse("app/static/frontend_client.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

