# app/api/endpoints.py
from fastapi import APIRouter, HTTPException, Depends, Query
from app.models.schemas import QuestionRequest, AnswerResponse, CompleteAnalysisRequest, CompleteAnalysisResponse
from app.services.process_question import process_question, retrieve_stats
from app.services.token_utils import contar_tokens, count_words, validar_palabras, reducir_contenido_por_palabras
from app.services.db_service import persistir_consulta
from app.services.prompt_service import get_system_prompt  # Nueva importación
# Importar funciones de health check
from app.api.health_check import health_check_endpoint, health_check_json
import json
import os
import configparser
import logging
import tiktoken
import datetime
import traceback
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import model_name, collection_name_fragmento, qdrant_url, max_results, openai_api_key
from app.core.logging_config import log_message, get_logger
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store_endpoint, get_llm
import sqlite3
import pymysql
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# Obtener el logger
logger = get_logger()

router = APIRouter(prefix="/api")

# Variable global para almacenar el ID del prompt actual
current_prompt_id = None

# Función para obtener el prompt del sistema dinámicamente
def get_sistema_prompt_base():
    """
    Obtiene el prompt base del sistema desde la base de datos con fallbacks.
    Registra en el log de dónde se obtuvo el prompt.
    Retorna una tupla (prompt_content, prompt_id).
    """
    global current_prompt_id
    
    try:
        prompt_content, source, prompt_id = get_system_prompt()
        
        # Almacenar el ID globalmente
        current_prompt_id = prompt_id
        
        # Registrar en el log la fuente del prompt y su ID
        if source == "base_de_datos":
            logger.info(f"PROMPT_LOADED: Prompt cargado desde base de datos - ID: {prompt_id}")
        elif source == "archivo_txt":
            logger.info(f"PROMPT_LOADED: Prompt cargado desde archivo {prompt_id}")
        elif source == "constante_hardcodeada":
            logger.warning("PROMPT_LOADED: Prompt cargado desde constante hardcodeada (fallback final)")
        
        return prompt_content, prompt_id
        
    except Exception as e:
        logger.error(f"Error al obtener prompt del sistema: {e}")
        logger.warning("PROMPT_LOADED: Usando prompt hardcodeado de emergencia debido a error")
        current_prompt_id = "emergency_fallback"
        return "Hola, soy tu asistente. ¿En qué puedo ayudarte?", "emergency_fallback"

@router.post("/process_question", response_model=AnswerResponse)
def handle_question(request: QuestionRequest):
    logger.info(f"[DEBUG-API] Recibida solicitud con datos: {request}")
    logger.info(f"[DEBUG-API] Pregunta: {request.question_input}")
    logger.info(f"[DEBUG-API] Fecha desde: {request.fecha_desde}")
    logger.info(f"[DEBUG-API] Fecha hasta: {request.fecha_hasta}")
    logger.info(f"[DEBUG-API] k: {request.k}")
    
    answer = process_question(
        request.question_input,
        request.fecha_desde,
        request.fecha_hasta,
        request.k
    )
    
    # Acceder a la misma instancia de RetrieveStats que se actualizó en process_question
    document_count = retrieve_stats.document_count
    
    logger.info(f"[DEBUG-API] Documentos recuperados: {document_count}")
    logger.info(f"[DEBUG-API] Respuesta generada: {answer}")
    
    return {
        "answer": answer,
        "metadata": {
            "document_count": document_count,
            "model": model_name
        }
    }

# Función para registrar un resumen de tokens
def log_token_summary(tokens_entrada, tokens_salida, modelo):
    cantidad_fragmentos = retrieve_stats.document_count
    
    separador = "=" * 80
    log_message(separador)
    log_message("RESUMEN DE CONTEO DE TOKENS (Qdrant)")
    log_message(f"Fecha y hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Modelo: {modelo}")
    log_message(f"Versión del prompt: {current_prompt_id if current_prompt_id else 'No disponible'}")
    log_message(separador)
    log_message(f"FRAGMENTOS RECUPERADOS DE LA BD VECTORIAL QDRANT: {cantidad_fragmentos}")
    log_message(f"TOKENS DE ENTRADA (pregunta + contexto): {tokens_entrada}")
    log_message(f"TOKENS DE SALIDA (respuesta final): {tokens_salida}")
    log_message(f"TOTAL TOKENS CONSUMIDOS: {tokens_entrada + tokens_salida}")
    
    # Calcular costo aproximado
    costo_aprox = 0
    
    if modelo.startswith("gpt-4"):
        costo_entrada = round((tokens_entrada / 1000) * 0.03, 4)
        costo_salida = round((tokens_salida / 1000) * 0.06, 4)
        costo_aprox = costo_entrada + costo_salida
    elif modelo.startswith("gpt-3.5"):
        costo_aprox = round(((tokens_entrada + tokens_salida) / 1000) * 0.002, 4)
    
    log_message(f"COSTO APROXIMADO USD: ${costo_aprox}")
    log_message(separador)
    
    # Guardar en formato JSON para análisis posterior
    resumen_json = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": modelo,
        "prompt_id": current_prompt_id,
        "fragments_count": cantidad_fragmentos,
        "input_tokens": tokens_entrada,
        "output_tokens": tokens_salida,
        "total_tokens": tokens_entrada + tokens_salida,
        "approx_cost_usd": costo_aprox,
        "vector_db": "Qdrant"
    }
    
    log_message(f"RESUMEN_JSON: {json.dumps(resumen_json)}")
    log_message(separador)
    
    return resumen_json

# Endpoint actualizado para el análisis completo con Qdrant
@router.post("/complete_analysis", response_model=CompleteAnalysisResponse)
async def handle_complete_analysis(
    request: CompleteAnalysisRequest,
    embeddings: OpenAIEmbeddings = Depends(get_embeddings),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    vector_store: Qdrant = Depends(get_vector_store_endpoint),
    llm: ChatOpenAI = Depends(get_llm)
):
    """
    Endpoint que integra todo el proceso de análisis de texto completo
    usando Qdrant como base de datos vectorial
    """
    # Línea divisoria para mejor visualización en logs
    log_message("="*80)
    log_message(f"##############-------INICIO COMPLETE_ANALYSIS (Qdrant)----------#####################")
    log_message(f"[DEBUG-COMPLETE] Recibida solicitud completa con datos: {request}")
    
    try:
        # Iniciamos el procesamiento y marcamos la hora de inicio
        start_time = datetime.datetime.now()
        
        # Obtener identificadores si están disponibles como parámetros
        id_usuario = getattr(request, 'id_usuario', None)
        ugel_origen = getattr(request, 'ugel_origen', None)
        
        # Marcar esto como consulta proveniente de API
        log_message(f"CLIENTE_API: Recibida consulta para análisis completo con Qdrant.")
        log_message(f"ID Usuario: {id_usuario if id_usuario else 'No especificado'}")
        log_message(f"UGL Origen: {ugel_origen if ugel_origen else 'No especificada'}")
        
        # Vamos a eliminar las inicializaciones de conteo de tokens que se calculan al final
        # y usar solo un punto de cálculo
        
        # Diccionario para registrar tokens por cada nodo (solo para análisis detallado)
        tokens_por_nodo = {
            "query_or_respond": {"entrada": 0, "salida": 0},
            "tools": {"entrada": 0, "salida": 0},
            "generate": {"entrada": 0, "salida": 0}
        }
        
        log_message(f"Iniciando ejecución del grafo LangGraph...")
        
        # Función de retrieve adaptada para Qdrant
        def retrieve(query: str):
            """Recuperar información relacionada con la consulta usando Qdrant."""
            log_message(f"########### RETRIEVE (Qdrant) --------#####################")
            
            # Contamos tokens de la consulta
            tokens_consulta = contar_tokens(query, model_name)
            log_message(f"Tokens de entrada en retrieve (consulta): {tokens_consulta}")
            
            # Usar valor del config.ini, ignorando el del request
            k_value = max_results
            log_message(f"Buscando documentos relevantes con k={k_value} (valor del config.ini)")
            
            # Realizar búsqueda en Qdrant
            try:
                retrieved_docs = vector_store.similarity_search_with_score(query, k=k_value)
                documentos_relevantes = [doc for doc, score in retrieved_docs]
                cantidad_fragmentos = len(documentos_relevantes)
                
                # Guardamos la cantidad de fragmentos
                retrieve_stats.document_count = cantidad_fragmentos
                
                if not documentos_relevantes:
                    log_message("No se encontró información suficiente para responder la pregunta.")
                    return "Lo siento, no tengo información suficiente para responder esa pregunta."
                
                # Formato detallado para el log
                formatted_docs = "\n\n".join(
                    (f"FRAGMENTO #{i+1}: {doc.page_content}\nMETADATA: {doc.metadata}\nSCORE: {score}")
                    for i, (doc, score) in enumerate(retrieved_docs)
                )
                log_message(f"Documentos recuperados:\n{formatted_docs}")
                
                serialized = "\n\n".join(
                    (f"fFRAGMENTO{doc.page_content}\nMETADATA{doc.metadata}") for doc in documentos_relevantes
                )
                
                # Contamos tokens de la respuesta de retrieve
                tokens_respuesta_retrieve = contar_tokens(serialized, model_name)
                log_message(f"Fragmentos recuperados de Qdrant: {cantidad_fragmentos}")
                log_message(f"Tokens de salida en retrieve: {tokens_respuesta_retrieve}")
                log_message(f"Total tokens en retrieve: {tokens_consulta + tokens_respuesta_retrieve}")
                
                # Log del contenido completo recuperado (como en versión Chroma)
                log_message(f"WEB-RETREIVE----> :\n {serialized} \n----------END-WEB-RETRIEBE <")
                
                return serialized
            except Exception as e:
                error_msg = f"Error al realizar la búsqueda en Qdrant: {str(e)}"
                log_message(error_msg, level='ERROR')
                log_message(traceback.format_exc(), level='ERROR')
                return "Error al buscar en la base de datos: no se pudo recuperar información relevante."
        
        # Nodo 1: Generar consulta o responder directamente
        def query_or_respond(state: MessagesState):
            """Genera una consulta para la herramienta de recuperación o responde directamente."""
            log_message(f"########### QUERY OR RESPOND ---------#####################")
            
            # Contamos tokens de entrada
            prompt_text = "\n".join([msg.content for msg in state["messages"]])
            tokens_entrada_qor = contar_tokens(prompt_text, model_name)
            log_message(f"Tokens de entrada en query_or_respond: {tokens_entrada_qor}")
            
            # Log del mensaje completo
            log_message(f"Estado de mensajes entrante: {state}")
            
            llm_with_tools = llm.bind_tools([retrieve])
            response = llm_with_tools.invoke(state["messages"])
            
            # Contamos tokens de salida
            tokens_salida_qor = contar_tokens(response.content, model_name)
            log_message(f"Tokens de salida en query_or_respond: {tokens_salida_qor}")
            log_message(f"Total tokens en query_or_respond: {tokens_entrada_qor + tokens_salida_qor}")
            
            # Log de la respuesta completa
            log_message(f"Respuesta de query_or_respond: {response.content}")
            
            return {"messages": [response]}
        
        # Nodo 2: Ejecutar la herramienta de recuperación
        tools = ToolNode([retrieve])
        
        # Nodo 3: Generar la respuesta final
        def generate(state: MessagesState):
            """Genera la respuesta final usando los documentos recuperados."""
            log_message(f"###########WEB-generate---------#####################")
            
            # Extraer mensajes de herramienta recientes
            recent_tool_messages = [msg for msg in reversed(state["messages"]) if msg.type == "tool"]
            log_message(f"Mensajes de herramienta encontrados: {len(recent_tool_messages)}")
            
            docs_content = "\n\n".join(doc.content for doc in recent_tool_messages[::-1])
            
            # Log del contenido de documentos
            log_message(f"Contenido de documentos compilados:\n{docs_content[:1000]}... (truncado)")
            
            # Validar si los documentos contienen términos clave de la pregunta
            user_question = state["messages"][0].content.lower()
            terms = user_question.split()
            
            log_message(f"Términos de búsqueda de la pregunta: {terms}")
            
            if not any(term in docs_content.lower() for term in terms):
                log_message("No se encontraron términos de la pregunta en los documentos, enviando respuesta genérica.")
                return {"messages": [{"role": "assistant", "content": "Lo siento, no tengo información suficiente para responder esa pregunta."}]}
            
            system_message_content = get_sistema_prompt_base()[0] + docs_content
       
            # Validar si excede el límite de palabras
            es_valido, num_palabras = validar_palabras(system_message_content)
            log_message(f"Sistema message contiene {num_palabras} palabras. Válido: {es_valido}")
            
            if not es_valido:
                # Reducir el contenido si es necesario
                system_message_content = reducir_contenido_por_palabras(get_sistema_prompt_base()[0] + docs_content) # Asegurarse que se usa la base + docs para reducir
                log_message(f"Se ha reducido el contenido a {count_words(system_message_content)} palabras.")
                log_message(f"WEB-CONTEXTO_QUEDO RESUMIDO ASI (system_message_content\n): {system_message_content[:1000]}... (truncado)")
            
            prompt = [SystemMessage(content=system_message_content)] + [
                msg for msg in state["messages"] if msg.type in ("human", "system")
            ]
            
            # Log del prompt completo
            log_message(f"WEB-PROMPT PROMPT ------>\n {prompt}--<")
            
            # Contamos tokens del prompt de entrada
            prompt_text = system_message_content + "\n" + "\n".join([msg.content for msg in state["messages"] if msg.type in ("human", "system")])
            tokens_entrada = contar_tokens(prompt_text, model_name)
            log_message(f"Tokens de entrada (prompt): {tokens_entrada}")
            
            # Realizamos la inferencia
            log_message(f"Generando respuesta final con modelo {model_name}")
            response = llm.invoke(prompt)
            
            # Contamos tokens de la respuesta
            tokens_salida = contar_tokens(response.content, model_name)
            log_message(f"Tokens de entrada (respuesta) DE PREGUNTA:: {tokens_entrada}")
            log_message(f"Tokens de salida (respuesta) DE PREGUNTA:: {tokens_salida}")
            log_message(f"Total tokens consumidos DE PREGUNTA: {tokens_entrada + tokens_salida}")
            
            # Añadimos un resumen del conteo de tokens
            token_summary = log_token_summary(tokens_entrada, tokens_salida, model_name)
            
            # Log de la respuesta completa
            log_message(f"WEB-PROMPT RESPONSE ------>\n {response}--<")
            
            return {"messages": [response]}
        
        # Construcción del gráfico de conversación
        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node(query_or_respond)
        graph_builder.add_node(tools)
        graph_builder.add_node(generate)
        graph_builder.set_entry_point("query_or_respond")
        graph_builder.add_edge("query_or_respond", "tools")
        graph_builder.add_edge("tools", "generate")
        graph = graph_builder.compile()
        
        # Procesar la pregunta
        log_message(f"##############-------PROCESANDO COMPLETE_ANALYSIS (Qdrant)----------#####################")
        
        # Preparar el mensaje con la pregunta y contexto - Usar valores del config.ini
        question_with_context = f"""
Pregunta: {request.question_input}
"""
        
        # Agregar información del usuario y UGL al contexto si están disponibles
        if id_usuario and ugel_origen:
            log_message(f"Agregando información de usuario (ID: {id_usuario}) y UGL ({ugel_origen}) al contexto")
            
        # Registramos tokens de la pregunta inicial
        tokens_pregunta = contar_tokens(question_with_context, model_name)
        log_message(f"Tokens de la pregunta inicial: {tokens_pregunta}")
        log_message(f"Pregunta con contexto: {question_with_context}")
        
        # Preparar el mensaje para el grafo
        human_message = HumanMessage(content=question_with_context)
        
        # Iniciar el streaming del grafo
        response_content = None
        
        try:
            # Iniciamos el procesamiento y marcamos la hora de inicio
            start_time = datetime.datetime.now()
            
            # Obtener identificadores si están disponibles como parámetros
            id_usuario = getattr(request, 'id_usuario', None)
            ugel_origen = getattr(request, 'ugel_origen', None)
            
            # Marcar esto como consulta proveniente de API
            log_message(f"CLIENTE_API: Recibida consulta para análisis completo con Qdrant.")
            log_message(f"ID Usuario: {id_usuario if id_usuario else 'No especificado'}")
            log_message(f"UGL Origen: {ugel_origen if ugel_origen else 'No especificada'}")
            
            # Vamos a eliminar las inicializaciones de conteo de tokens que se calculan al final
            # y usar solo un punto de cálculo
            
            # Diccionario para registrar tokens por cada nodo (solo para análisis detallado)
            tokens_por_nodo = {
                "query_or_respond": {"entrada": 0, "salida": 0},
                "tools": {"entrada": 0, "salida": 0},
                "generate": {"entrada": 0, "salida": 0}
            }
            
            log_message(f"Iniciando ejecución del grafo LangGraph...")
            
            last_step = None
            step_count = 0
            for step in graph.stream(
                {"messages": [human_message]},
                stream_mode="values",
                config={"configurable": {"thread_id": "user_question"}}
            ):
                step_count += 1
                last_step = step
                log_message(f"Ejecutando paso {step_count} del grafo...")
                
                # Si hay mensajes y el último es del asistente, extraemos la respuesta
                if "messages" in step and step["messages"]:
                    assistant_messages = [msg for msg in step["messages"] 
                                        if hasattr(msg, 'type') and msg.type == "ai" or
                                            hasattr(msg, 'role') and msg.role == "assistant"]
                    
                    if assistant_messages:
                        latest_assistant_msg = assistant_messages[-1]
                        if hasattr(latest_assistant_msg, 'content'):
                            response_content = latest_assistant_msg.content
                            log_message(f"Respuesta parcial actualizada en paso {step_count}")
            
            log_message(f"Grafo completado con {step_count} pasos.")
            
            # Si no tenemos respuesta pero tenemos último paso
            if response_content is None and last_step and "messages" in last_step:
                log_message("No se encontró respuesta en el streaming, buscando en el último paso...")
                for msg in reversed(last_step["messages"]):
                    if (hasattr(msg, 'type') and msg.type == "ai") or \
                    (hasattr(msg, 'role') and msg.role == "assistant"):
                        response_content = msg.content
                        log_message("Respuesta encontrada en el último paso")
                        break
            
            # Si aún no hay respuesta
            if response_content is None:
                log_message("No se pudo extraer ninguna respuesta del grafo. Usando respuesta genérica.")
                response_content = "Lo siento, no se pudo generar una respuesta."
            
            # Registrar resultado
            log_message(f"Respuesta final generada, longitud: {len(response_content)}")
            
            # Calcular tiempo total
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            tiempo_respuesta_ms = int(processing_time * 1000)
            log_message(f"TIEMPO RESPUESTA: {processing_time:.2f} segundos ({tiempo_respuesta_ms} ms)")
            
            # CÁLCULO ÚNICO DE TOKENS - Hacerlo una sola vez aquí
            # 1. Tokens de la pregunta del usuario
            tokens_pregunta_usuario = contar_tokens(question_with_context, model_name)
            log_message(f"Tokens de la pregunta del usuario (question_with_context): {tokens_pregunta_usuario}")

            # 2. Tokens del prompt base del sistema
            tokens_prompt_sistema_base = contar_tokens(get_sistema_prompt_base()[0], model_name)
            log_message(f"Tokens del prompt base del sistema (get_sistema_prompt_base): {tokens_prompt_sistema_base}")

            # 3. Tokens del contexto recuperado (docs_content)
            # Extraer docs_content del último estado del grafo (last_step)
            # Replicamos la lógica de cómo se construye docs_content en el nodo 'generate'
            docs_content_final = ""
            if last_step and "messages" in last_step:
                tool_messages = [msg for msg in reversed(last_step["messages"]) if hasattr(msg, 'type') and msg.type == "tool"]
                if tool_messages:
                    docs_content_final = "\n\n".join(doc.content for doc in tool_messages[::-1])
                    log_message(f"docs_content_final extraído del last_step, longitud: {len(docs_content_final)}")
                else:
                    log_message("No se encontraron mensajes de herramienta en el last_step para extraer docs_content_final.")
            else:
                log_message("last_step no disponible o no contiene mensajes para extraer docs_content_final.")

            tokens_documentos_contexto = contar_tokens(docs_content_final, model_name)
            log_message(f"Tokens del contexto recuperado (docs_content_final): {tokens_documentos_contexto}")

            # Suma total de tokens de entrada
            tokens_entrada = tokens_pregunta_usuario + tokens_prompt_sistema_base + tokens_documentos_contexto
            
            # Calcular tokens de salida (esto parece correcto)
            tokens_salida = contar_tokens(response_content, model_name)
            
            # Usar estos valores para logs y base de datos
            log_message(f"CÁLCULO ÚNICO DE TOKENS (REVISADO):")
            log_message(f"Tokens de pregunta usuario: {tokens_pregunta_usuario}")
            log_message(f"Tokens de prompt sistema base: {tokens_prompt_sistema_base}")
            log_message(f"Tokens de documentos (contexto): {tokens_documentos_contexto}")
            log_message(f"Tokens de entrada (total): {tokens_entrada}")
            log_message(f"Tokens de salida (respuesta): {tokens_salida}")
            log_message(f"Total tokens consumidos: {tokens_entrada + tokens_salida}")
            
            # Generar resumen de tokens para los logs
            token_summary = log_token_summary(tokens_entrada, tokens_salida, model_name)
            
            log_message(f"##############-------FIN COMPLETE_ANALYSIS (Qdrant)----------#####################")
            log_message("="*80)
            
            # Agregar versión del prompt al final de la respuesta
            if current_prompt_id:
                response_content += f"\nvp:{current_prompt_id}"
                log_message(f"Versión del prompt agregada a la respuesta: {current_prompt_id}")
            
            # Persistir en base de datos con los mismos valores calculados
            try:
                # Parámetros para la función persistir_consulta
                id_nueva_consulta = persistir_consulta(
                    pregunta_usuario=request.question_input,
                    respuesta_asistente=response_content,
                    id_usuario=id_usuario if id_usuario else 321,  # Valor por defecto según las reglas
                    ugel_origen=ugel_origen if ugel_origen else "Formosa",  # Valor por defecto según las reglas
                    tokens_input=tokens_entrada,  # Usar el valor calculado
                    tokens_output=tokens_salida,  # Usar el valor calculado
                    tiempo_respuesta_ms=tiempo_respuesta_ms,
                    id_prompt_usado=current_prompt_id,  # Usar ID del prompt en lugar de versión
                    comentario=None,  # Por ahora sin comentario
                    error_detectado=False,
                    modelo_llm_usado=model_name
                )
                if id_nueva_consulta:
                    log_message(f"Se inserto Consulta/Pregunta con ID: {id_nueva_consulta} en la base de datos.")
                else:
                    log_message(f"Error al persistir consulta en base de datos (no se obtuvo ID).", level="ERROR")
            except Exception as e:
                log_message(f"Error al persistir consulta en base de datos: {str(e)}", level="ERROR")
            
            # Retornar la respuesta a la API
            return {
                "answer": response_content,
                "metadata": {
                    "document_count": retrieve_stats.document_count,
                    "model": model_name,
                    "processing_time_ms": tiempo_respuesta_ms,
                    "input_tokens": tokens_entrada,
                    "output_tokens": tokens_salida,
                    "total_tokens": tokens_entrada + tokens_salida,
                    "id_usuario": id_usuario if id_usuario is not None else 321,
                    "ugel_origen": ugel_origen if ugel_origen is not None else "Formosa",
                    "id_consulta": id_nueva_consulta if 'id_nueva_consulta' in locals() and id_nueva_consulta is not None else None
                }
            }
            
        except Exception as e:
            log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}", level="ERROR")
            log_message(traceback.format_exc(), level="ERROR")
            
            # Calcular tiempo de procesamiento
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0
            tiempo_respuesta_ms = int(processing_time * 1000)
            log_message(f"TIEMPO RESPUESTA (ERROR): {processing_time:.2f} segundos ({tiempo_respuesta_ms} ms)")
            
            # Preparar mensaje de error
            error_message = f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
            response_content = "Lo siento, ocurrió un error en el servidor. Por favor, intenta nuevamente más tarde."
            
            # Agregar versión del prompt al final de la respuesta de error
            if current_prompt_id:
                response_content += f"\nvp:{current_prompt_id}"
                log_message(f"Versión del prompt agregada a la respuesta de error: {current_prompt_id}")
            
            # CÁLCULO ÚNICO DE TOKENS EN CASO DE ERROR (también necesita revisión)
            tokens_entrada_error = 0 # Renombrar para evitar colisión con el caso exitoso
            tokens_salida_error = 0  # Renombrar para evitar colisión

            # Si ya teníamos la pregunta, calculamos sus tokens
            if 'question_with_context' in locals() and question_with_context:
                tokens_pregunta_usuario_error = contar_tokens(question_with_context, model_name)
                tokens_entrada_error += tokens_pregunta_usuario_error
                log_message(f"Tokens de entrada (pregunta) en error: {tokens_pregunta_usuario_error}")

            # En caso de error, es posible que docs_content_final no se haya podido generar o no sea relevante.
            # Sin embargo, si el error ocurrió después de la recuperación, podríamos intentar incluirlo.
            # Por simplicidad y consistencia con la idea de que el LLM no procesó el contexto completo,
            # podríamos omitir los tokens del sistema y del contexto para el cálculo de tokens_entrada en caso de error,
            # o solo incluir la pregunta. Para este ejemplo, seremos conservadores.
            # Si el error ocurre antes del nodo 'generate', get_sistema_prompt_base() y docs_content_final no se habrían usado.
            # El `token_summary` ya usa los tokens que se le pasan, así que el log será coherente.

            # Se usa get_sistema_prompt_base()[0] para el cálculo en caso de error
            tokens_prompt_sistema_base_error = contar_tokens(get_sistema_prompt_base()[0], model_name)

            # No intentaremos extraer docs_content_final en caso de error general, ya que el grafo pudo no completarse.

            # Tokens de la respuesta de error
            tokens_salida_error = contar_tokens(response_content, model_name) # response_content es el mensaje de error
            log_message(f"Tokens de salida (respuesta de error): {tokens_salida_error}")
            
            # Registrar resumen de tokens incluso en caso de error
            # Usamos tokens_entrada_error y tokens_salida_error
            token_summary_error = log_token_summary(tokens_entrada_error, tokens_salida_error, model_name)
            
            # Persistir error en base de datos con los mismos valores calculados
            try:
                id_consulta_error = persistir_consulta(
                    pregunta_usuario=request.question_input,
                    respuesta_asistente=response_content,
                    id_usuario=id_usuario if id_usuario else 321,
                    ugel_origen=ugel_origen if ugel_origen else "Formosa",
                    tokens_input=tokens_entrada_error, # Usar tokens_entrada_error
                    tokens_output=tokens_salida_error,  # Usar tokens_salida_error
                    tiempo_respuesta_ms=tiempo_respuesta_ms,
                    id_prompt_usado=current_prompt_id,  # Usar ID del prompt en lugar de versión
                    comentario=None,  # Por ahora sin comentario
                    error_detectado=True,
                    tipo_error="Error en procesamiento",
                    mensaje_error=str(e),
                    modelo_llm_usado=model_name
                )
                if id_consulta_error:
                    log_message(f"Se inserto Consulta/Pregunta de ERROR con ID: {id_consulta_error} en la base de datos.")
                else:
                    log_message("Error al persistir la consulta de error en base de datos (no se obtuvo ID).", level="ERROR")

            except Exception as db_error:
                log_message(f"Error al persistir el error en base de datos: {str(db_error)}", level="ERROR")
            
            # Retornar respuesta de error con los mismos valores de tokens
            return {
                "answer": response_content,
                "metadata": {
                    "error": True,
                    "error_message": str(e),
                    "model": model_name,
                    "processing_time_ms": tiempo_respuesta_ms,
                    "input_tokens": tokens_entrada_error,
                    "output_tokens": tokens_salida_error,
                    "total_tokens": tokens_entrada_error + tokens_salida_error,
                    "id_usuario": id_usuario if id_usuario is not None else 321,
                    "ugel_origen": ugel_origen if ugel_origen is not None else "Formosa",
                    "id_consulta": id_consulta_error if 'id_consulta_error' in locals() and id_consulta_error is not None else None
                }
            }
    
    except Exception as e:
        log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}", level="ERROR")
        log_message(traceback.format_exc(), level="ERROR")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Cargar variables de entorno. Ajusta la ruta si es necesario.
# Usualmente, si .env está en la raíz del proyecto y ejecutas desde ahí, no se necesita dotenv_path.
# Pero si ejecutas endpoints.py directamente o desde otro subdirectorio, podría ser útil.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env') # Sube dos niveles desde app/api/
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    # Fallback si no se encuentra en la ruta esperada, intenta cargar desde el directorio actual o raíz
    load_dotenv()

# Modelo Pydantic para la solicitud de feedback
class FeedbackRequest(BaseModel):
    id_consulta: int
    feedback_value: str # Esperamos "me_gusta" o "no_me_gusta"

# Modelo Pydantic para la respuesta de cada consulta
class ConsultaAdminItem(BaseModel):
    id_consulta: int
    timestamp: datetime.datetime # FastAPI manejará la serialización a string ISO
    id_usuario: int
    ugel_origen: str
    pregunta_usuario_completa: str # Nombre cambiado para claridad
    pregunta_usuario_truncada: str
    respuesta_asistente_completa: str # Nombre cambiado para claridad
    respuesta_asistente_truncada: str
    respuesta_es_vacia: bool
    respuesta_util: str # Cambiado de bool a str para soportar "si", "no", "nada"
    tokens_input: int
    tokens_output: int
    tiempo_respuesta_ms: int

# Modelo Pydantic para la solicitud de comentarios
class CommentRequest(BaseModel):
    id_consulta: int
    comentario: str

@router.post("/comentario", summary="Registrar comentario para una consulta")
async def handle_comentario(request: CommentRequest):
    logger.info("--- INICIO Endpoint /api/comentario ---")
    logger.info(f"Recibida solicitud de comentario RAW: {request}")

    id_consulta = request.id_consulta
    comentario_texto = request.comentario.strip()
    logger.info(f"Procesando comentario para id_consulta: {id_consulta}, comentario: {comentario_texto[:50]}...")

    if not comentario_texto:
        logger.warning(f"Comentario vacío para id_consulta: {id_consulta}")
        raise HTTPException(status_code=400, detail="El comentario no puede estar vacío.")

    if len(comentario_texto) > 255:
        logger.warning(f"Comentario muy largo para id_consulta: {id_consulta} (longitud: {len(comentario_texto)})")
        raise HTTPException(status_code=400, detail="El comentario no puede exceder 255 caracteres.")

    conn = None 
    try:
        logger.info(f"Intentando obtener conexión a la BD para comentario (id_consulta: {id_consulta})")
        conn = get_admin_db_connection() 
        if not conn:
            logger.error(f"Fallo al conectar a la BD para comentario (id_consulta: {id_consulta})")
            raise HTTPException(status_code=503, detail="Error de conexión a la base de datos.")

        logger.info(f"Conexión a BD exitosa para comentario (id_consulta: {id_consulta})")
        cursor = conn.cursor()
        
        # Detectar el tipo de BD real
        db_type_real = "sqlite"  # Por defecto SQLite
        try:
            if hasattr(conn, 'server_version'):  # Atributo específico de pymysql
                db_type_real = "mysql"
            elif str(type(conn)).find('sqlite') != -1:  # Verificar si es SQLite
                db_type_real = "sqlite"
        except:
            db_type_real = "sqlite"  # Fallback a SQLite
            
        logger.info(f"Tipo de BD real detectado: {db_type_real}")

        # Primero verificar si existe la consulta
        if db_type_real == 'mysql':
            check_query = "SELECT id_consulta FROM consultas WHERE id_consulta = %s"
            cursor.execute(check_query, (id_consulta,))
        else:  # sqlite
            check_query = "SELECT id_consulta FROM consultas WHERE id_consulta = ?"
            cursor.execute(check_query, (id_consulta,))
        
        existing_record = cursor.fetchone()
        if not existing_record:
            logger.warning(f"No se encontró consulta con id_consulta={id_consulta}")
            raise HTTPException(status_code=404, detail=f"No se encontró la consulta con ID {id_consulta}.")

        logger.info(f"Consulta {id_consulta} encontrada, procediendo con el update de comentario")

        # Realizar el UPDATE
        if db_type_real == 'mysql':
            sql_update_query = """
                UPDATE consultas
                SET comentario = %s
                WHERE id_consulta = %s
            """
            params_tuple = (comentario_texto, id_consulta)
        else:  # sqlite
            sql_update_query = """
                UPDATE consultas
                SET comentario = ?
                WHERE id_consulta = ?
            """
            params_tuple = (comentario_texto, id_consulta)
        
        logger.info(f"Ejecutando UPDATE para comentario (id_consulta: {id_consulta}): Query: {sql_update_query.strip()} con Params: {params_tuple}")
        cursor.execute(sql_update_query, params_tuple)
        
        rows_affected = cursor.rowcount if hasattr(cursor, 'rowcount') else 1
        logger.info(f"Filas afectadas por el UPDATE: {rows_affected}")
        
        conn.commit()
        logger.info(f"Commit de la transacción realizado para comentario (id_consulta: {id_consulta})")

        # Verificar que el update fue exitoso
        if db_type_real == 'mysql':
            verify_query = "SELECT comentario FROM consultas WHERE id_consulta = %s"
            cursor.execute(verify_query, (id_consulta,))
        else:  # sqlite
            verify_query = "SELECT comentario FROM consultas WHERE id_consulta = ?"
            cursor.execute(verify_query, (id_consulta,))
        
        updated_record = cursor.fetchone()
        if updated_record:
            if isinstance(updated_record, dict):  # MySQL
                actual_value = updated_record['comentario']
            else:  # SQLite
                actual_value = updated_record[0]
            
            logger.info(f"Verificación: comentario actualizado para id_consulta: {id_consulta}")
            
            if actual_value == comentario_texto:
                logger.info(f"Comentario actualizado correctamente para id_consulta: {id_consulta}")
                return {
                    "status": "success", 
                    "message": "Comentario guardado correctamente", 
                    "id_consulta": id_consulta, 
                    "comentario_guardado": comentario_texto
                }
            else:
                logger.error(f"Error: el comentario no se actualizó correctamente para id_consulta: {id_consulta}")
                raise HTTPException(status_code=500, detail="Error al actualizar el comentario en la base de datos.")
        else:
            logger.error(f"Error: no se pudo verificar la actualización del comentario para id_consulta: {id_consulta}")
            raise HTTPException(status_code=500, detail="Error al verificar la actualización del comentario.")

    except HTTPException as http_exc:
        logger.error(f"HTTPException en /api/comentario (id_consulta: {id_consulta}): {http_exc.detail}")
        raise http_exc 
    except Exception as e:
        if conn:
            logger.info(f"Realizando rollback debido a excepción en /api/comentario (id_consulta: {id_consulta})")
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Error durante rollback: {rollback_error}")
        
        logger.error(f"Error EXCEPCIÓN GENERAL al actualizar comentario para id_consulta {id_consulta}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar comentario.")
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as close_error:
                logger.error(f"Error al cerrar cursor: {close_error}")
            try:
                conn.close()
            except Exception as close_error:
                logger.error(f"Error al cerrar conexión: {close_error}")
            logger.info(f"Conexión a BD (comentario) cerrada para id_consulta: {id_consulta}")
        logger.info("--- FIN Endpoint /api/comentario ---")

# --- Función de conexión a la BD (similar a la anterior, pero sin ser parte de Flask) ---
def get_admin_db_connection():
    conn = None
    db_type_admin = os.getenv('DB_TYPE', 'sqlite') # Usar una variable diferente o la misma si la config es igual
    
    logger.info(f"get_admin_db_connection: Intentando conectar con DB_TYPE={db_type_admin}")
    
    # Intentar con MySQL primero si está configurado
    if db_type_admin == 'mysql':
        try:
            logger.info(f"Intentando conexión MySQL: host={os.getenv('BD_SERVER')}, port={os.getenv('BD_PORT', 3306)}, user={os.getenv('BD_USER')}, db={os.getenv('BD_NAME')}")
            
            conn = pymysql.connect(
                host=os.getenv('BD_SERVER'),
                port=int(os.getenv('BD_PORT', 3306)),
                user=os.getenv('BD_USER'),
                password=os.getenv('BD_PASSWD'),
                database=os.getenv('BD_NAME'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor, # Devuelve filas como diccionarios
                connect_timeout=60,
                autocommit=False  # Asegurarse de que autocommit esté desactivado
            )
            
            # Verificar la conexión
            with conn.cursor() as test_cursor:
                test_cursor.execute("SELECT 1 as test")
                test_result = test_cursor.fetchone()
                logger.info(f"Test de conexión MySQL exitoso: {test_result}")
            
            logger.info("Conectado a MySQL para admin exitosamente.")
            return conn
            
        except Exception as e:
            logger.error(f"Error al conectar a MySQL para admin: {e}")
            logger.error(traceback.format_exc())
            logger.info("Intentando con SQLite como alternativa...")
            # No retornar aún, intentar con SQLite
    else:
        logger.info("DB_TYPE no es mysql, usando SQLite directamente.")
    
    # Si no es MySQL o falló la conexión a MySQL, intentar con SQLite
    try:
        # Ajusta la ruta a tu archivo SQLite según sea necesario
        # Esta ruta es relativa al punto de ejecución del script.
        # Si .env define SQLITE_PATH, debería ser una ruta absoluta o relativa al CWD.
        sqlite_path_admin = os.getenv('SQLITE_PATH', 'BD_RELA/local_database.db')
        
        logger.info(f"Intentando conexión SQLite con path: {sqlite_path_admin}")
        
        # Verificar si el archivo existe
        if not os.path.exists(sqlite_path_admin):
            logger.warning(f"SQLite file not found at {sqlite_path_admin}, looking in alternate locations")
            # Intentar con ubicaciones alternativas
            alt_paths = [
                'db/simap_assistant.db',
                'BD_RELA/local_database.db',
                '../BD_RELA/local_database.db'
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    sqlite_path_admin = alt_path
                    logger.info(f"Found SQLite database at alternate location: {sqlite_path_admin}")
                    break
        
        conn = sqlite3.connect(sqlite_path_admin)
        conn.row_factory = sqlite3.Row # Para acceder a columnas por nombre
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Verificar la conexión
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        test_result = cursor.fetchone()
        logger.info(f"Test de conexión SQLite exitoso: {test_result}")
        cursor.close()
        
        logger.info(f"Conectado a SQLite para admin en: {sqlite_path_admin}")
        return conn
        
    except Exception as e:
        logger.error(f"Error al conectar a SQLite para admin: {e}")
        logger.error(traceback.format_exc())
        return None

# Nuevo endpoint para la interfaz de administración de consultas
@router.get("/admin/consultas_filtradas", response_model=List[ConsultaAdminItem])
async def obtener_consultas_filtradas_admin(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    respuesta_es_vacia: Optional[int] = Query(None, description="Filtrar por respuesta vacía (1 para Sí, 0 para No)"),
    respuesta_util: Optional[str] = Query(None, description="Filtrar por respuesta útil ('si', 'no', 'nada')")
):
    try:
        conn = get_admin_db_connection()
        if not conn:
            logger.error("OBTENER_CONSULTAS_FILTRADAS: No se pudo obtener conexión a la BD.")
            raise HTTPException(status_code=503, detail="Error de conexión a la base de datos.")
            
        cursor = conn.cursor()

        # Determinar el tipo de base de datos activa para esta conexión
        db_type_actual = 'sqlite'  # Valor por defecto
        if hasattr(conn, 'server_version'):  # pymysql.connections.Connection tiene 'server_version'
            db_type_actual = 'mysql'
        
        logger.info(f"OBTENER_CONSULTAS_FILTRADAS: Tipo de BD detectado para construcción de query: {db_type_actual}")
        placeholder = '?' if db_type_actual == 'sqlite' else '%s'

        # Construir la consulta SQL base
        base_query_select_part = """
            SELECT 
                id_consulta,
                timestamp,
                id_usuario,
                ugel_origen,
                pregunta_usuario,
                respuesta_asistente,
                respuesta_es_vacia,
                respuesta_util,
                tokens_input,
                tokens_output,
                tiempo_respuesta_ms
            FROM consultas
        """
        
        conditions = []
        current_params = []

        # Agregar filtros según los parámetros recibidos
        if fecha_desde:
            conditions.append(f"DATE(timestamp) >= {placeholder}")
            current_params.append(fecha_desde)
        
        if fecha_hasta:
            conditions.append(f"DATE(timestamp) <= {placeholder}")
            current_params.append(fecha_hasta)
        
        if respuesta_es_vacia is not None:
            conditions.append(f"respuesta_es_vacia = {placeholder}")
            current_params.append(respuesta_es_vacia)
        
        # Asegurarse que el filtro respuesta_util solo se aplique si tiene un valor relevante
        if respuesta_util is not None and respuesta_util != "": 
            conditions.append(f"respuesta_util = {placeholder}")
            current_params.append(respuesta_util)

        if conditions:
            final_query = base_query_select_part + " WHERE " + " AND ".join(conditions)
        else:
            # Si no hay condiciones, se seleccionan todos los registros
            final_query = base_query_select_part
            
        final_query += " ORDER BY timestamp DESC"

        logger.info(f"OBTENER_CONSULTAS_FILTRADAS: Query final: {final_query}")
        logger.info(f"OBTENER_CONSULTAS_FILTRADAS: Parámetros: {tuple(current_params)}")

        cursor.execute(final_query, tuple(current_params))
        rows = cursor.fetchall()
        
        # Procesar los resultados
        results = []
        for row in rows:
            # Determinar si estamos trabajando con un diccionario (MySQL) o una tupla/Row (SQLite)
            if isinstance(row, dict):
                # MySQL con DictCursor
                pregunta_completa = row['pregunta_usuario'] or ""
                respuesta_completa = row['respuesta_asistente'] or ""
                result = {
                    "id_consulta": row['id_consulta'],
                    "timestamp": row['timestamp'],
                    "id_usuario": row['id_usuario'],
                    "ugel_origen": row['ugel_origen'],
                    "pregunta_usuario_completa": pregunta_completa,
                    "pregunta_usuario_truncada": pregunta_completa[:50] + "..." if len(pregunta_completa) > 50 else pregunta_completa,
                    "respuesta_asistente_completa": respuesta_completa,
                    "respuesta_asistente_truncada": respuesta_completa[:50] + "..." if len(respuesta_completa) > 50 else respuesta_completa,
                    "respuesta_es_vacia": bool(row['respuesta_es_vacia']),
                    "respuesta_util": row['respuesta_util'] if row['respuesta_util'] is not None else "nada",
                    "tokens_input": row['tokens_input'] if row['tokens_input'] is not None else 0,
                    "tokens_output": row['tokens_output'] if row['tokens_output'] is not None else 0,
                    "tiempo_respuesta_ms": row['tiempo_respuesta_ms'] if row['tiempo_respuesta_ms'] is not None else 0
                }
            else:
                # SQLite con Row o tupla
                pregunta_completa = row[4] if row[4] is not None else ""
                respuesta_completa = row[5] if row[5] is not None else ""
                result = {
                    "id_consulta": row[0],
                    "timestamp": row[1],
                    "id_usuario": row[2],
                    "ugel_origen": row[3],
                    "pregunta_usuario_completa": pregunta_completa,
                    "pregunta_usuario_truncada": pregunta_completa[:50] + "..." if len(pregunta_completa) > 50 else pregunta_completa,
                    "respuesta_asistente_completa": respuesta_completa,
                    "respuesta_asistente_truncada": respuesta_completa[:50] + "..." if len(respuesta_completa) > 50 else respuesta_completa,
                    "respuesta_es_vacia": bool(row[6]),
                    "respuesta_util": row[7] if row[7] is not None else "nada",
                    "tokens_input": row[8] if row[8] is not None else 0,
                    "tokens_output": row[9] if row[9] is not None else 0,
                    "tiempo_respuesta_ms": row[10] if row[10] is not None else 0
                }
            
            results.append(result)
        
        cursor.close()
        conn.close()
        
        return results

    except Exception as e:
        logger.error(f"Error al obtener consultas filtradas: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback", summary="Registrar feedback para una consulta")
async def handle_feedback(request: FeedbackRequest):
    logger.info("--- INICIO Endpoint /api/feedback ---")
    logger.info(f"Recibida solicitud de feedback RAW: {request}")

    id_consulta = request.id_consulta
    feedback_str = request.feedback_value
    logger.info(f"Procesando feedback para id_consulta: {id_consulta}, valor: {feedback_str}")

    if feedback_str not in ["me_gusta", "no_me_gusta"]:
        logger.warning(f"Valor de feedback no válido: {feedback_str} para id_consulta: {id_consulta}")
        raise HTTPException(status_code=400, detail="Valor de feedback no válido. Use 'me_gusta' o 'no_me_gusta'.")

    # Mapear "me_gusta" a "si" y "no_me_gusta" a "no"
    respuesta_util_valor = "si" if feedback_str == "me_gusta" else "no"
    logger.info(f"Mapeado a respuesta_util (string): {respuesta_util_valor}")

    conn = None 
    try:
        logger.info(f"Intentando obtener conexión a la BD para feedback (id_consulta: {id_consulta})")
        conn = get_admin_db_connection() 
        if not conn:
            logger.error(f"Fallo al conectar a la BD para feedback (id_consulta: {id_consulta})")
            raise HTTPException(status_code=503, detail="Error de conexión a la base de datos.")

        logger.info(f"Conexión a BD exitosa para feedback (id_consulta: {id_consulta})")
        
        # Detectar el tipo de BD real basándose en la conexión, no en la variable de entorno
        # Esto es importante porque DB_TYPE puede ser 'mysql' pero usar SQLite como fallback
        db_type_real = "sqlite"  # Por defecto SQLite
        try:
            # Método más robusto para detectar el tipo de conexión
            if hasattr(conn, 'server_version'):  # Atributo específico de pymysql
                db_type_real = "mysql"
                logger.info(f"Detectado MySQL con server_version: {conn.server_version}")
            elif str(type(conn)).find('sqlite') != -1:  # Verificar si es SQLite
                db_type_real = "sqlite"
                logger.info(f"Detectado SQLite: {type(conn)}")
            elif hasattr(conn, 'get_server_info'):  # Método alternativo para MySQL
                db_type_real = "mysql"
                logger.info(f"Detectado MySQL con get_server_info: {conn.get_server_info()}")
        except Exception as detect_error:
            logger.warning(f"Error al detectar tipo de BD, usando SQLite por defecto: {detect_error}")
            db_type_real = "sqlite"  # Fallback a SQLite
            
        logger.info(f"Tipo de BD real detectado: {db_type_real}")

        cursor = conn.cursor()

        # Primero verificar si existe la consulta
        if db_type_real == 'mysql':
            check_query = "SELECT id_consulta FROM consultas WHERE id_consulta = %s"
            logger.info(f"Ejecutando query de verificación MySQL: {check_query} con parámetro: {id_consulta}")
            cursor.execute(check_query, (id_consulta,))
        else:  # sqlite
            check_query = "SELECT id_consulta FROM consultas WHERE id_consulta = ?"
            logger.info(f"Ejecutando query de verificación SQLite: {check_query} con parámetro: {id_consulta}")
            cursor.execute(check_query, (id_consulta,))
        
        existing_record = cursor.fetchone()
        logger.info(f"Resultado de verificación: {existing_record}")
        
        if not existing_record:
            logger.warning(f"No se encontró consulta con id_consulta={id_consulta}")
            raise HTTPException(status_code=404, detail=f"No se encontró la consulta con ID {id_consulta}.")

        logger.info(f"Consulta {id_consulta} encontrada, procediendo con el update")

        # Realizar el UPDATE
        if db_type_real == 'mysql':
            sql_update_query = """
                UPDATE consultas
                SET respuesta_util = %s
                WHERE id_consulta = %s
            """
            params_tuple = (respuesta_util_valor, id_consulta)
        else:  # sqlite
            sql_update_query = """
                UPDATE consultas
                SET respuesta_util = ?
                WHERE id_consulta = ?
            """
            params_tuple = (respuesta_util_valor, id_consulta)
        
        logger.info(f"Ejecutando UPDATE para feedback (id_consulta: {id_consulta}): Query: {sql_update_query.strip()} con Params: {params_tuple}")
        
        try:
            cursor.execute(sql_update_query, params_tuple)
            rows_affected = cursor.rowcount if hasattr(cursor, 'rowcount') else 1
            logger.info(f"Filas afectadas por el UPDATE: {rows_affected}")
            
            # Commit de la transacción
            conn.commit()
            logger.info(f"Commit de la transacción realizado para feedback (id_consulta: {id_consulta})")
            
        except Exception as update_error:
            logger.error(f"Error durante el UPDATE: {update_error}")
            logger.error(traceback.format_exc())
            raise

        # Verificar que el update fue exitoso consultando el registro actualizado
        if db_type_real == 'mysql':
            verify_query = "SELECT respuesta_util FROM consultas WHERE id_consulta = %s"
            logger.info(f"Ejecutando query de verificación MySQL: {verify_query} con parámetro: {id_consulta}")
            cursor.execute(verify_query, (id_consulta,))
        else:  # sqlite
            verify_query = "SELECT respuesta_util FROM consultas WHERE id_consulta = ?"
            logger.info(f"Ejecutando query de verificación SQLite: {verify_query} con parámetro: {id_consulta}")
            cursor.execute(verify_query, (id_consulta,))
        
        updated_record = cursor.fetchone()
        logger.info(f"Resultado de verificación después del update: {updated_record}")
        
        if updated_record:
            if isinstance(updated_record, dict):  # MySQL
                actual_value = updated_record['respuesta_util']
                logger.info(f"Valor extraído de dict (MySQL): {actual_value}")
            else:  # SQLite
                actual_value = updated_record[0] if isinstance(updated_record, tuple) else updated_record['respuesta_util']
                logger.info(f"Valor extraído de row (SQLite): {actual_value}")
            
            logger.info(f"Verificación: respuesta_util actualizada a '{actual_value}' para id_consulta: {id_consulta}")
            
            if actual_value == respuesta_util_valor:
                logger.info(f"Feedback actualizado correctamente para id_consulta: {id_consulta}")
                return {
                    "status": "success", 
                    "message": "Gracias por tu opinión!", 
                    "id_consulta": id_consulta, 
                    "respuesta_util_actualizada": respuesta_util_valor,
                    "db_type": db_type_real  # Agregar para debugging
                }
            else:
                logger.error(f"Error: el valor no se actualizó correctamente. Esperado: {respuesta_util_valor}, Actual: {actual_value}")
                raise HTTPException(status_code=500, detail="Error al actualizar el feedback en la base de datos.")
        else:
            logger.error(f"Error: no se pudo verificar la actualización para id_consulta: {id_consulta}")
            raise HTTPException(status_code=500, detail="Error al verificar la actualización del feedback.")

    except HTTPException as http_exc:
        logger.error(f"HTTPException en /api/feedback (id_consulta: {id_consulta}): {http_exc.detail}")
        raise http_exc 
    except Exception as e:
        if conn:
            logger.info(f"Realizando rollback debido a excepción en /api/feedback (id_consulta: {id_consulta})")
            try:
                conn.rollback()
                logger.info("Rollback completado")
            except Exception as rollback_error:
                logger.error(f"Error durante rollback: {rollback_error}")
        
        logger.error(f"Error EXCEPCIÓN GENERAL al actualizar feedback para id_consulta {id_consulta}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar feedback: {str(e)}")
    finally:
        if conn:
            try:
                if hasattr(conn, 'cursor') and cursor:
                    cursor.close()
                    logger.info("Cursor cerrado")
            except Exception as close_error:
                logger.error(f"Error al cerrar cursor: {close_error}")
            try:
                conn.close()
                logger.info("Conexión cerrada")
            except Exception as close_error:
                logger.error(f"Error al cerrar conexión: {close_error}")
            logger.info(f"Conexión a BD (feedback) cerrada para id_consulta: {id_consulta}")
        logger.info("--- FIN Endpoint /api/feedback ---")

# Clase para el formato de datos de estadísticas
class EstadisticasResponse(BaseModel):
    total_preguntas: int
    total_tokens_input: int
    total_tokens_output: int
    utilidad: Dict[str, int]
    respuesta_vacia: Dict[str, int]
    ugel_preguntas: List[Dict[str, Any]]

# Modelo Pydantic para la respuesta del gráfico de respuesta_util
class RespuestaUtilChartResponse(BaseModel):
    labels: List[str]
    values: List[int]

# Endpoint para obtener las UGELs disponibles
@router.get("/admin/ugels_disponibles", response_model=List[str], summary="Obtener UGELs Disponibles")
async def obtener_ugels_disponibles():
    """
    Obtiene la lista de UGELs únicas registradas en la base de datos
    """
    conn = get_admin_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos para admin.")

    try:
        cursor = conn.cursor()
        
        query = """
            SELECT DISTINCT ugel_origen 
            FROM consultas 
            WHERE ugel_origen IS NOT NULL AND ugel_origen != ''
            ORDER BY ugel_origen
        """
        
        cursor.execute(query)
        ugels_raw = cursor.fetchall()
        
        # Extraer los valores de UGEL del resultado
        ugels_list = []
        for row in ugels_raw:
            if isinstance(row, dict):  # Para MySQL (DictCursor)
                ugel = row.get('ugel_origen')
            else:  # Para SQLite (Row)
                ugel = row['ugel_origen']
                
            if ugel and ugel not in ugels_list:
                ugels_list.append(ugel)
                
        return ugels_list
        
    except Exception as e:
        logger.error(f"Error al obtener UGELs disponibles: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("Conexión a BD (admin) cerrada.")

# Endpoint para obtener estadísticas de respuesta_util para el gráfico
@router.get("/admin/stats/respuesta_util_por_fecha", response_model=RespuestaUtilChartResponse, summary="Estadísticas de Utilidad de Respuesta por Fecha")
async def obtener_stats_respuesta_util(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Obtiene la cuenta de cada valor en `respuesta_util` para un rango de fechas.
    Diseñado para ser consumido por un gráfico de barras en el frontend.
    Devuelve los datos agrupados listos para Chart.js.
    """
    conn = get_admin_db_connection()
    if not conn:
        logger.error("STATS_RESPUESTA_UTIL: Error al conectar a la BD.")
        raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos para admin.")

    try:
        cursor = conn.cursor()
        db_type_admin = os.getenv('DB_TYPE', 'sqlite')
        logger.info(f"STATS_RESPUESTA_UTIL: Iniciando consulta. DB_TYPE: {db_type_admin}")

        filtros_sql = []
        params_sql = {} 
        params_list_sql = []

        if fecha_desde:
            try:
                fecha_desde_dt = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
                if db_type_admin == 'mysql':
                    filtros_sql.append("timestamp >= %(fecha_desde)s")
                    params_sql['fecha_desde'] = fecha_desde_dt
                else: 
                    filtros_sql.append("timestamp >= ?")
                    params_list_sql.append(fecha_desde_dt)
            except ValueError:
                logger.warning(f"STATS_RESPUESTA_UTIL: Formato de fecha_desde inválido: {fecha_desde}")
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Usar YYYY-MM-DD.")

        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
                if db_type_admin == 'mysql':
                    filtros_sql.append("timestamp <= %(fecha_hasta)s")
                    params_sql['fecha_hasta'] = fecha_hasta_dt
                else: 
                    filtros_sql.append("timestamp <= ?")
                    params_list_sql.append(fecha_hasta_dt)
            except ValueError:
                logger.warning(f"STATS_RESPUESTA_UTIL: Formato de fecha_hasta inválido: {fecha_hasta}")
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Usar YYYY-MM-DD.")
        
        where_clause = ""
        if filtros_sql:
            where_clause = " WHERE " + " AND ".join(filtros_sql)

        query_stats = f"""
            SELECT 
                COALESCE(LOWER(respuesta_util), 'sin clasificar') as categoria_utilidad,
                COUNT(*) as cantidad
            FROM consultas
            {where_clause}
            GROUP BY categoria_utilidad
            ORDER BY cantidad DESC
        """
        # Se agrega LOWER() para unificar 'si', 'Si', 'SI', etc. y COALESCE para agrupar nulos.

        logger.info(f"STATS_RESPUESTA_UTIL: Query: {query_stats}")
        if db_type_admin == 'mysql':
            logger.info(f"STATS_RESPUESTA_UTIL: Params (MySQL): {params_sql}")
            cursor.execute(query_stats, params_sql)
        else:
            logger.info(f"STATS_RESPUESTA_UTIL: Params (SQLite): {tuple(params_list_sql)}")
            cursor.execute(query_stats, tuple(params_list_sql))
            
        results = cursor.fetchall()

        labels = []
        values = []
        if results:
            for row in results:
                # Asegurar que la etiqueta sea un string
                label_from_db = str(row['categoria_utilidad'] if isinstance(row, dict) else row[0])
                value_from_db = int(row['cantidad'] if isinstance(row, dict) else row[1])
                labels.append(label_from_db)
                values.append(value_from_db)
        
        logger.info(f"STATS_RESPUESTA_UTIL: Resultados para gráfico: Labels: {labels}, Values: {values}")
        return RespuestaUtilChartResponse(labels=labels, values=values)

    except HTTPException as http_exc: # Re-lanzar HTTPExceptions para que FastAPI las maneje
        logger.error(f"STATS_RESPUESTA_UTIL: HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"STATS_RESPUESTA_UTIL: Error inesperado: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al generar estadísticas de utilidad: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("STATS_RESPUESTA_UTIL: Conexión a BD cerrada.")

# Endpoint para obtener estadísticas generales
@router.get("/admin/estadisticas", response_model=EstadisticasResponse, summary="Obtener Estadísticas Generales")
async def obtener_estadisticas(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    ugel_origen: Optional[str] = Query(None, description="UGEL origen específica")
):
    """
    Obtiene estadísticas basadas en los filtros aplicados
    """
    conn = get_admin_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos para admin.")

    try:
        cursor = conn.cursor()
        
        # Construir condiciones de filtrado
        filtros_sql = []
        params_sql = {}  # Para MySQL
        params_list_sql = []  # Para SQLite

        db_type_admin = os.getenv('DB_TYPE', 'sqlite')

        # Construir filtros
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
                if db_type_admin == 'mysql':
                    filtros_sql.append("timestamp >= %(fecha_desde)s")
                    params_sql['fecha_desde'] = fecha_desde_dt
                else:  # sqlite
                    filtros_sql.append("timestamp >= ?")
                    params_list_sql.append(fecha_desde_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Usar YYYY-MM-DD.")

        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
                if db_type_admin == 'mysql':
                    filtros_sql.append("timestamp <= %(fecha_hasta)s")
                    params_sql['fecha_hasta'] = fecha_hasta_dt
                else:  # sqlite
                    filtros_sql.append("timestamp <= ?")
                    params_list_sql.append(fecha_hasta_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Usar YYYY-MM-DD.")
                
        if ugel_origen:
            if db_type_admin == 'mysql':
                filtros_sql.append("ugel_origen = %(ugel_origen)s")
                params_sql['ugel_origen'] = ugel_origen
            else:  # sqlite
                filtros_sql.append("ugel_origen = ?")
                params_list_sql.append(ugel_origen)
                
        # Crear cláusula WHERE si hay filtros
        where_clause = ""
        if filtros_sql:
            where_clause = " WHERE " + " AND ".join(filtros_sql)
        
        # 1. Contar total de preguntas
        query_total = f"SELECT COUNT(*) as total FROM consultas{where_clause}"
        
        if db_type_admin == 'mysql':
            cursor.execute(query_total, params_sql)
        else:
            cursor.execute(query_total, tuple(params_list_sql))
            
        total_result = cursor.fetchone()
        total_preguntas = total_result['total'] if isinstance(total_result, dict) else total_result[0]
        
        # 2. Sumar tokens
        query_tokens = f"""
            SELECT 
                SUM(COALESCE(tokens_input, 0)) as total_input,
                SUM(COALESCE(tokens_output, 0)) as total_output
            FROM consultas
            {where_clause}
        """
        
        if db_type_admin == 'mysql':
            cursor.execute(query_tokens, params_sql)
        else:
            cursor.execute(query_tokens, tuple(params_list_sql))
            
        tokens_result = cursor.fetchone()
        
        if isinstance(tokens_result, dict):
            total_tokens_input = tokens_result['total_input'] or 0
            total_tokens_output = tokens_result['total_output'] or 0
        else:
            total_tokens_input = tokens_result[0] or 0
            total_tokens_output = tokens_result[1] or 0
        
        # 3. Estadísticas de utilidad
        query_utilidad = f"""
            SELECT 
                respuesta_util,
                COUNT(*) as cantidad
            FROM consultas
            {where_clause}
            GROUP BY respuesta_util
        """
        
        if db_type_admin == 'mysql':
            cursor.execute(query_utilidad, params_sql)
        else:
            cursor.execute(query_utilidad, tuple(params_list_sql))
            
        utilidad_results = cursor.fetchall()
        
        # Inicializar contadores
        utilidad_si = 0
        utilidad_no = 0
        utilidad_sin_clasificar = 0
        
        for row in utilidad_results:
            if isinstance(row, dict):
                util_val = row['respuesta_util']
                cantidad = row['cantidad']
            else:
                util_val = row[0]
                cantidad = row[1]
                
            if util_val == 'si':
                utilidad_si = cantidad
            elif util_val == 'no':
                utilidad_no = cantidad
            else:
                utilidad_sin_clasificar += cantidad
        
        # 4. Estadísticas de respuestas vacías
        query_vacia = f"""
            SELECT 
                respuesta_es_vacia,
                COUNT(*) as cantidad
            FROM consultas
            {where_clause}
            GROUP BY respuesta_es_vacia
        """
        
        if db_type_admin == 'mysql':
            cursor.execute(query_vacia, params_sql)
        else:
            cursor.execute(query_vacia, tuple(params_list_sql))
            
        vacia_results = cursor.fetchall()
        
        # Inicializar contadores
        vacia_si = 0
        vacia_no = 0
        vacia_sin_clasificar = 0
        
        for row in vacia_results:
            if isinstance(row, dict):
                vacia_val = row['respuesta_es_vacia']
                cantidad = row['cantidad']
            else:
                vacia_val = row[0]
                cantidad = row[1]
                
            if vacia_val == 1:
                vacia_si = cantidad
            elif vacia_val == 0:
                vacia_no = cantidad
            else:
                vacia_sin_clasificar += cantidad
        
        # 5. Preguntas por UGEL
        query_ugel = f"""
            SELECT 
                COALESCE(ugel_origen, 'Sin UGEL') as ugel,
                COUNT(*) as cantidad
            FROM consultas
            {where_clause}
            GROUP BY ugel_origen
            ORDER BY cantidad DESC
        """
        
        if db_type_admin == 'mysql':
            cursor.execute(query_ugel, params_sql)
        else:
            cursor.execute(query_ugel, tuple(params_list_sql))
            
        ugel_results = cursor.fetchall()
        
        ugel_data = []
        for row in ugel_results:
            if isinstance(row, dict):
                ugel_nombre = row['ugel'] or 'Sin definir'
                cantidad = row['cantidad']
            else:
                ugel_nombre = row[0] or 'Sin definir'
                cantidad = row[1]
                
            ugel_data.append({
                "ugel": ugel_nombre,
                "cantidad": cantidad
            })
        
        # Construir la respuesta final
        respuesta = {
            "total_preguntas": total_preguntas,
            "total_tokens_input": total_tokens_input,
            "total_tokens_output": total_tokens_output,
            "utilidad": {
                "si": utilidad_si,
                "no": utilidad_no,
                "sin_clasificar": utilidad_sin_clasificar
            },
            "respuesta_vacia": {
                "si": vacia_si,
                "no": vacia_no,
                "sin_clasificar": vacia_sin_clasificar
            },
            "ugel_preguntas": ugel_data
        }
        
        return respuesta
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("Conexión a BD (admin) cerrada.")

# Modelo Pydantic para la respuesta de estadísticas diarias
class EstadisticasDiariasResponse(BaseModel):
    fecha: str
    cantidad: int

@router.get("/admin/stats/registros_por_dia", response_model=List[EstadisticasDiariasResponse])
async def obtener_stats_diarias(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Obtiene la cantidad de registros por día para un rango de fechas.
    """
    conn = get_admin_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos para admin.")

    try:
        cursor = conn.cursor()
        db_type = os.getenv('DB_TYPE', 'sqlite')
        
        # Construir filtros
        filtros_sql = []
        params_sql = {}  # Para MySQL
        params_list_sql = []  # Para SQLite

        if fecha_desde:
            try:
                fecha_desde_dt = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
                if db_type == 'mysql':
                    filtros_sql.append("timestamp >= %(fecha_desde)s")
                    params_sql['fecha_desde'] = fecha_desde_dt
                else:  # sqlite
                    filtros_sql.append("timestamp >= ?")
                    params_list_sql.append(fecha_desde_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Usar YYYY-MM-DD.")

        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
                if db_type == 'mysql':
                    filtros_sql.append("timestamp <= %(fecha_hasta)s")
                    params_sql['fecha_hasta'] = fecha_hasta_dt
                else:  # sqlite
                    filtros_sql.append("timestamp <= ?")
                    params_list_sql.append(fecha_hasta_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Usar YYYY-MM-DD.")

        # Crear cláusula WHERE si hay filtros
        where_clause = ""
        if filtros_sql:
            where_clause = " WHERE " + " AND ".join(filtros_sql)

        # Query adaptada según el tipo de base de datos
        if db_type == 'mysql':
            query = f"""
                SELECT DATE(timestamp) as fecha, COUNT(*) as cantidad
                FROM consultas
                {where_clause}
                GROUP BY DATE(timestamp)
                ORDER BY fecha ASC
            """
        else:  # sqlite
            query = f"""
                SELECT date(timestamp) as fecha, COUNT(*) as cantidad
                FROM consultas
                {where_clause}
                GROUP BY date(timestamp)
                ORDER BY fecha ASC
            """

        if db_type == 'mysql':
            cursor.execute(query, params_sql)
        else:
            cursor.execute(query, tuple(params_list_sql))

        resultados = cursor.fetchall()
        
        # Procesar resultados
        stats_diarias = []
        for row in resultados:
            if isinstance(row, dict):  # MySQL
                fecha = row['fecha']
                cantidad = row['cantidad']
            else:  # SQLite
                fecha = row[0]
                cantidad = row[1]
            
            # Asegurar que la fecha sea un string en formato YYYY-MM-DD
            if isinstance(fecha, (datetime.date, datetime.datetime)):
                fecha = fecha.strftime('%Y-%m-%d')
            
            stats_diarias.append({
                "fecha": fecha,
                "cantidad": cantidad
            })

        return stats_diarias

    except Exception as e:
        logger.error(f"Error al obtener estadísticas diarias: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# Añadir endpoints de health check al final del archivo, antes de la última línea

@router.get("/health", summary="Diagnóstico HTML del Sistema")
async def health_check_html():
    """
    Endpoint que muestra un diagnóstico completo del sistema en formato HTML.
    Verifica el estado de Uvicorn, Qdrant, bases de datos, OpenAI y scripts críticos.
    """
    return await health_check_endpoint()

@router.get("/health/json", summary="Diagnóstico JSON del Sistema")
async def health_check_data():
    """
    Endpoint que retorna el diagnóstico del sistema en formato JSON.
    Útil para monitoreo automatizado o integración con otros sistemas.
    """
    return await health_check_json()

@router.get("/status", summary="Estado Básico del Sistema")
async def basic_status():
    """
    Endpoint simple que retorna el estado básico del sistema.
    Útil para verificaciones rápidas de disponibilidad.
    """
    try:
        from app.api.health_check import HealthChecker
        checker = HealthChecker()
        
        # Hacer verificaciones básicas
        uvicorn_check = checker.check_uvicorn_status()
        qdrant_check = checker.check_qdrant_connection()
        
        if uvicorn_check["status"] == "OK" and qdrant_check["status"] == "OK":
            return {
                "status": "OK",
                "message": "Sistema operativo",
                "timestamp": datetime.datetime.now().isoformat(),
                "components": {
                    "uvicorn": "OK",
                    "qdrant": "OK"
                }
            }
        else:
            return {
                "status": "ERROR",
                "message": "Sistema con problemas",
                "timestamp": datetime.datetime.now().isoformat(),
                "components": {
                    "uvicorn": uvicorn_check["status"],
                    "qdrant": qdrant_check["status"]
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en verificación básica: {str(e)}")
