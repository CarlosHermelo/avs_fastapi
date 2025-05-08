# app/core/dependencies.py
from fastapi import Depends
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from app.core.config import model_name, collection_name_fragmento, qdrant_url, openai_api_key
from app.core.logging_config import log_message, get_logger
import traceback
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from openai import RateLimitError, APITimeoutError, APIConnectionError, APIError

logger = get_logger()

# Inicializar una vez y reutilizar
_embeddings = None
_qdrant_client = None
_vector_store = None
_llm = None

# Configuración de reintento para OpenAI
@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError, APIError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=before_sleep_log(logger, logger.level)
)
def create_embeddings_with_retry(api_key):
    """Crea la instancia de OpenAIEmbeddings con reintentos"""
    return OpenAIEmbeddings(api_key=api_key)

@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError, APIError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=before_sleep_log(logger, logger.level)
)
def create_llm_with_retry(model, temperature, api_key):
    """Crea la instancia de ChatOpenAI con reintentos"""
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)

# Configuración de reintento para Qdrant
@retry(
    retry=retry_if_exception_type((UnexpectedResponse, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logger.level)
)
def create_qdrant_client_with_retry(url):
    """Crea la instancia de QdrantClient con reintentos"""
    return QdrantClient(url=url)

@retry(
    retry=retry_if_exception_type((UnexpectedResponse, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logger.level)
)
def check_collection_with_retry(client, collection_name):
    """Verifica que la colección existe con reintentos"""
    return client.get_collection(collection_name)

def get_embeddings():
    """Devuelve una instancia singleton de OpenAIEmbeddings"""
    global _embeddings
    if _embeddings is None:
        logger.info("Inicializando OpenAIEmbeddings (singleton)")
        api_key_prefix = openai_api_key[:10] if len(openai_api_key) > 10 else openai_api_key
        logger.info(f"Usando API key que comienza con: {api_key_prefix}...")
        try:
            _embeddings = create_embeddings_with_retry(openai_api_key)
            logger.info("OpenAIEmbeddings inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar OpenAIEmbeddings después de múltiples intentos: {str(e)}")
            logger.error(traceback.format_exc())
            # Creamos una versión básica sin reintentos como fallback
            _embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    return _embeddings

def get_qdrant_client():
    """Devuelve una instancia singleton de QdrantClient"""
    global _qdrant_client
    if _qdrant_client is None:
        logger.info(f"Inicializando QdrantClient (singleton) en: {qdrant_url}")
        try:
            _qdrant_client = create_qdrant_client_with_retry(qdrant_url)
            # Verificar que la colección existe
            try:
                check_collection_with_retry(_qdrant_client, collection_name_fragmento)
                logger.info(f"Colección {collection_name_fragmento} encontrada en Qdrant.")
            except Exception as e:
                error_msg = f"Error: La colección {collection_name_fragmento} no existe en Qdrant: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                # No lanzamos excepción aquí para permitir que la app inicie
        except Exception as e:
            logger.error(f"Error al conectar con Qdrant después de múltiples intentos: {str(e)}")
            logger.error(traceback.format_exc())
            # Creamos una versión básica sin reintentos como fallback
            _qdrant_client = QdrantClient(url=qdrant_url)
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
        try:
            _llm = create_llm_with_retry(model_name, 0, openai_api_key)
            logger.info("ChatOpenAI inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar ChatOpenAI después de múltiples intentos: {str(e)}")
            logger.error(traceback.format_exc())
            # Creamos una versión básica sin reintentos como fallback
            _llm = ChatOpenAI(model=model_name, temperature=0, api_key=openai_api_key)
    return _llm 