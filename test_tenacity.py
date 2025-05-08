#!/usr/bin/env python
"""
Script de prueba para verificar el manejo de errores con tenacity
en las llamadas a las APIs de OpenAI y Qdrant.
"""
import os
import time
import logging
import configparser
from tenacity import retry, stop_after_attempt, wait_exponential
from tenacity import retry_if_exception_type, before_sleep_log
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, APIError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar configuración
config = configparser.ConfigParser()
try:
    config.read('config.ini')
    openai_api_key = config['DEFAULT'].get('openai_api_key', None)
    qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
    collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store')
except Exception as e:
    logger.error(f"Error al cargar la configuración: {str(e)}")
    raise

# Prueba de conexión a OpenAI con reintentos
@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError, APIError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
def test_openai_connection(api_key):
    """Prueba la conexión a la API de OpenAI con reintentos"""
    logger.info("Probando conexión a OpenAI...")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": "Hola, ¿cómo estás?"}
        ],
        max_tokens=10
    )
    return response

# Prueba de conexión a Qdrant con reintentos
@retry(
    retry=retry_if_exception_type((UnexpectedResponse, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
def test_qdrant_connection(url):
    """Prueba la conexión a Qdrant con reintentos"""
    logger.info(f"Probando conexión a Qdrant en {url}...")
    client = QdrantClient(url=url)
    collections = client.get_collections()
    return collections

# Simulador de fallos (para probar los reintentos)
def run_with_simulated_failures(func, *args, **kwargs):
    """Ejecuta una función simulando fallos intermitentes para probar reintentos"""
    attempt = [0]
    
    def mock_with_failures(*args, **kwargs):
        attempt[0] += 1
        if attempt[0] <= 2:  # Simula 2 fallos antes de tener éxito
            logger.warning(f"Simulando fallo en intento {attempt[0]}")
            if func.__name__ == 'test_openai_connection':
                raise APIConnectionError("Error de conexión simulado")
            else:
                raise ConnectionError("Error de conexión simulado")
        return func(*args, **kwargs)
    
    return mock_with_failures(*args, **kwargs)

def main():
    logger.info("=== Inicio de pruebas de tenacity para manejo de errores de API ===")
    
    # Prueba 1: Conexión a OpenAI
    logger.info("\n--- Prueba 1: Conexión a OpenAI ---")
    try:
        response = test_openai_connection(openai_api_key)
        logger.info(f"Conexión a OpenAI exitosa. Respuesta: {response.choices[0].message.content}")
    except Exception as e:
        logger.error(f"Error en la conexión a OpenAI después de múltiples intentos: {str(e)}")
    
    # Prueba 2: Conexión a Qdrant
    logger.info("\n--- Prueba 2: Conexión a Qdrant ---")
    try:
        collections = test_qdrant_connection(qdrant_url)
        if hasattr(collections, 'collections'):
            collection_names = [c.name for c in collections.collections]
            logger.info(f"Conexión a Qdrant exitosa. Colecciones disponibles: {collection_names}")
            
            # Verificar si existe la colección que usamos
            if collection_name in collection_names:
                logger.info(f"La colección '{collection_name}' existe en Qdrant.")
            else:
                logger.warning(f"La colección '{collection_name}' NO existe en Qdrant.")
        else:
            logger.info(f"Conexión a Qdrant exitosa. Respuesta: {collections}")
    except Exception as e:
        logger.error(f"Error en la conexión a Qdrant después de múltiples intentos: {str(e)}")
    
    # Prueba 3: Simulación de fallos en OpenAI para probar reintentos
    logger.info("\n--- Prueba 3: Simulación de fallos en OpenAI ---")
    try:
        logger.info("Simulando fallos intermitentes en la conexión a OpenAI...")
        run_with_simulated_failures(test_openai_connection, openai_api_key)
        logger.info("Simulación de reintentos en OpenAI completada con éxito.")
    except Exception as e:
        logger.error(f"Error en la simulación de reintentos para OpenAI: {str(e)}")
    
    # Prueba 4: Simulación de fallos en Qdrant para probar reintentos
    logger.info("\n--- Prueba 4: Simulación de fallos en Qdrant ---")
    try:
        logger.info("Simulando fallos intermitentes en la conexión a Qdrant...")
        run_with_simulated_failures(test_qdrant_connection, qdrant_url)
        logger.info("Simulación de reintentos en Qdrant completada con éxito.")
    except Exception as e:
        logger.error(f"Error en la simulación de reintentos para Qdrant: {str(e)}")
    
    logger.info("\n=== Fin de las pruebas de tenacity ===")

if __name__ == "__main__":
    main() 