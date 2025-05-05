# app/core/dependencies.py
from fastapi import Depends
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from app.core.config import model_name, collection_name_fragmento, qdrant_url, openai_api_key
from app.core.logging_config import log_message, get_logger
import traceback

logger = get_logger()

# Inicializar una vez y reutilizar
_embeddings = None
_qdrant_client = None
_vector_store = None
_llm = None

def get_embeddings():
    """Devuelve una instancia singleton de OpenAIEmbeddings"""
    global _embeddings
    if _embeddings is None:
        logger.info("Inicializando OpenAIEmbeddings (singleton)")
        api_key_prefix = openai_api_key[:10] if len(openai_api_key) > 10 else openai_api_key
        logger.info(f"Usando API key que comienza con: {api_key_prefix}...")
        _embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    return _embeddings

def get_qdrant_client():
    """Devuelve una instancia singleton de QdrantClient"""
    global _qdrant_client
    if _qdrant_client is None:
        logger.info(f"Inicializando QdrantClient (singleton) en: {qdrant_url}")
        _qdrant_client = QdrantClient(url=qdrant_url)
        # Verificar que la colección existe
        try:
            _qdrant_client.get_collection(collection_name_fragmento)
            logger.info(f"Colección {collection_name_fragmento} encontrada en Qdrant.")
        except Exception as e:
            error_msg = f"Error: La colección {collection_name_fragmento} no existe en Qdrant: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            # No lanzamos excepción aquí para permitir que la app inicie
            # La excepción se manejará cuando se use el cliente en los endpoints
    return _qdrant_client

def get_vector_store():
    """Devuelve una instancia singleton de Qdrant vector store"""
    global _vector_store
    if _vector_store is None:
        logger.info(f"Inicializando Qdrant vector store (singleton) para colección: {collection_name_fragmento}")
        # Obtener las dependencias manualmente sin usar Depends
        embeddings = get_embeddings()
        qdrant_client = get_qdrant_client()
        _vector_store = Qdrant(
            client=qdrant_client,
            collection_name=collection_name_fragmento,
            embeddings=embeddings
        )
    return _vector_store

# Versión con Depends para usar en endpoints de FastAPI
def get_vector_store_endpoint(
    embeddings: OpenAIEmbeddings = Depends(get_embeddings),
    qdrant_client: QdrantClient = Depends(get_qdrant_client)
):
    """Versión para usar como dependencia en endpoints de FastAPI"""
    return get_vector_store()

def get_llm():
    """Devuelve una instancia singleton de ChatOpenAI"""
    global _llm
    if _llm is None:
        logger.info(f"Inicializando modelo LLM (singleton): {model_name}")
        _llm = ChatOpenAI(model=model_name, temperature=0, api_key=openai_api_key)
    return _llm 