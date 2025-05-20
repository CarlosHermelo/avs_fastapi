# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Importar el router de la API
from app.api import endpoints 
from app.core.logging_config import get_logger # Para el logger
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store, get_llm

# Obtener el logger
logger = get_logger()

app = FastAPI(
    title="Asistente Virtual SIMAP API MINIMAL", # Título MUY DISTINTO para prueba
    version="0.0.1-minimal", # Versión MUY DISTINTA para prueba
    description="Prueba mínima de FastAPI con CORS para verificar carga.", 
    openapi_url="/api/v1/openapi.json" 
)

logger.info("MAIN_MINIMAL: Aplicación FastAPI inicializada con nuevo título y versión.")

# Configurar CORS (Cross-Origin Resource Sharing)
origins = [
    "null",  # MUY IMPORTANTE: para permitir solicitudes desde file:///
    "http://localhost",
    "http://localhost:8000", 
    "http://127.0.0.1",
    "http://127.0.0.1:8000", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("MAIN_MINIMAL: CORSMiddleware añadido.")

# Inicializar recursos al arranque de la aplicación
@app.on_event("startup")
async def startup_event():
    logger.info("MAIN_MINIMAL: Evento startup iniciando...")
    try:
        get_embeddings() 
        get_qdrant_client()
        get_vector_store()
        get_llm()
        logger.info("MAIN_MINIMAL: Recursos singleton inicializados correctamente.")
    except Exception as e:
        logger.error(f"MAIN_MINIMAL: Error durante la inicialización de recursos: {e}", exc_info=True)

# Montar el directorio de archivos estáticos (app/static)
static_files_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_files_path) and os.path.isdir(static_files_path):
    app.mount("/static", StaticFiles(directory=static_files_path), name="static")
    logger.info(f"MAIN_MINIMAL: Directorio estático montado en: {static_files_path}")
else:
    logger.warning(f"MAIN_MINIMAL: Directorio estático NO encontrado en: {static_files_path}")

# Incluir el router de la API desde app.api.endpoints
app.include_router(endpoints.router) 
logger.info("MAIN_MINIMAL: Router de API incluido.")

@app.get("/minimal_root", summary="Endpoint Raíz de Prueba Mínima")
async def read_minimal_root():
    logger.info("MAIN_MINIMAL: Acceso a /minimal_root")
    return {
        "message": "API Mínima del Asistente Virtual SIMAP funcionando!",
        "title_should_be": app.title,
        "version_should_be": app.version,
        "documentation": app.docs_url,
        "openapi_schema": app.openapi_url,
    }

logger.info("MAIN_MINIMAL: Fin de la configuración de app/main.py (versión mínima).")

if __name__ == "__main__":
    import uvicorn
    logger.info("MAIN_MINIMAL: Ejecutando Uvicorn directamente desde main.py")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
