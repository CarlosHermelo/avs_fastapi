# app/services/process_question.py
from app.services.graph_logic import build_graph, retrieve_stats
from app.services.token_utils import contar_tokens, validar_palabras, reducir_contenido_por_palabras, count_words
from app.core.logging_config import log_message
import traceback
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import os
import datetime
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import model_name, max_results, collection_name_fragmento, qdrant_url, openai_api_key
from app.core.logging_config import get_logger
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store, get_llm
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# Obtener el logger
logger = get_logger()

def process_question(question, fecha_desde=None, fecha_hasta=None, k=None):
    """
    Procesa una pregunta y devuelve la respuesta
    """
    log_message(f"Procesando pregunta: {question}")
    
    try:
        # Crear el grafo
        graph, human_message = build_graph(question, fecha_desde, fecha_hasta, k, openai_api_key)
        
        # Ejecutar el grafo con estado inicial
        log_message("Iniciando ejecución del grafo...")
        result = graph.invoke({"messages": [human_message]})
        
        # Extraer la respuesta
        answer = None
        if "messages" in result and result["messages"]:
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'type') and msg.type == "ai" or hasattr(msg, 'role') and msg.role == "assistant":
                    answer = msg.content
                    break
        
        if not answer:
            answer = "No se pudo generar una respuesta."
    
    except Exception as e:
        logger.error(f"Error procesando la pregunta: {str(e)}")
        logger.error(traceback.format_exc())
        answer = f"Error al procesar la pregunta: {str(e)}"
    
    return answer

def log_token_summary(tokens_entrada, tokens_salida, fragmentos_count, modelo):
    """
    Registra un resumen claro del conteo de tokens para cada inferencia.
    
    Args:
        tokens_entrada (int): Número de tokens de la entrada (pregunta + contexto)
        tokens_salida (int): Número de tokens de la respuesta
        fragmentos_count (int): Número de fragmentos recuperados
        modelo (str): Nombre del modelo utilizado
    """
    separador = "=" * 80
    logger.info(separador)
    logger.info("RESUMEN DE CONTEO DE TOKENS (Qdrant)")
    logger.info(f"Fecha y hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Modelo: {modelo}")
    logger.info(separador)
    logger.info(f"FRAGMENTOS RECUPERADOS DE LA BD VECTORIAL QDRANT: {fragmentos_count}")
    logger.info(f"TOKENS DE ENTRADA (pregunta + contexto): {tokens_entrada}")
    logger.info(f"TOKENS DE SALIDA (respuesta final): {tokens_salida}")
    logger.info(f"TOTAL TOKENS CONSUMIDOS: {tokens_entrada + tokens_salida}")
    
    # Calcular costo aproximado
    costo_aprox = 0
    
    if modelo.startswith("gpt-4"):
        costo_entrada = round((tokens_entrada / 1000) * 0.03, 4)
        costo_salida = round((tokens_salida / 1000) * 0.06, 4)
        costo_aprox = costo_entrada + costo_salida
    elif modelo.startswith("gpt-3.5"):
        costo_aprox = round(((tokens_entrada + tokens_salida) / 1000) * 0.002, 4)
    
    logger.info(f"COSTO APROXIMADO USD: ${costo_aprox}")
    logger.info(separador)
    
    # Guardar en formato JSON para análisis posterior
    resumen_json = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": modelo,
        "fragments_count": fragmentos_count,
        "input_tokens": tokens_entrada,
        "output_tokens": tokens_salida,
        "total_tokens": tokens_entrada + tokens_salida,
        "approx_cost_usd": costo_aprox,
        "vector_db": "Qdrant"
    }
    
    logger.info(f"RESUMEN_JSON: {json.dumps(resumen_json)}")
    logger.info(separador)
    
    return resumen_json

if __name__ == "__main__":
    # Ejemplo de uso
    question = "¿Cómo es la afiliación de la esposa de un afiliado?"
    answer = process_question(question)
    print(f"Pregunta: {question}")
    print(f"Respuesta: {answer}")
    print(f"Documentos recuperados: {retrieve_stats.document_count}")

