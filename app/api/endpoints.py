# app/api/endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import QuestionRequest, AnswerResponse, CompleteAnalysisRequest, CompleteAnalysisResponse
from app.services.process_question import process_question, retrieve_stats
from app.services.token_utils import contar_tokens, count_words, validar_palabras, reducir_contenido_por_palabras
from app.services.db_service import persistir_consulta
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

# Obtener el logger
logger = get_logger()

router = APIRouter(prefix="/api")

# Definición de la constante para el prompt base del sistema
SISTEMA_PROMPT_BASE = """
<CONTEXTO>
La información proporcionada tiene como objetivo apoyar a los agentes que trabajan en las agencias de PAMI, quienes se encargan de atender las consultas de los afiliados. Este soporte está diseñado para optimizar la experiencia de atención al público y garantizar que los afiliados reciban información confiable y relevante en el menor tiempo posible.
</CONTEXTO>

<ROL>
 Eres un asistente virtual experto en los servicios y trámites de PAMI.
</ROL>
<TAREA>
   Tu tarea es responder preguntas relacionadas con lo trámites y servicios que ofrece la obra social PAMI, basándote únicamente en los datos disponibles en la base de datos vectorial. Si la información no está disponible, debes decir 'No tengo esa información en este momento'.
</TAREA>
<REGLAS_CRÍTICAS>
- **PROHIBIDO hacer inferencias, generalizaciones, deducciones o suposiciones sobre trámites, renovaciones, requisitos o períodos.**
- Si no existe una afirmación explícita, clara y literal en el contexto, responde exactamente: **"No tengo la informacion suficiente del SIMAP para responderte en forma precisa tu pregunta."**
- Cada afirmación incluida en tu respuesta debe tener respaldo textual directo en el contexto.
</REGLAS_CRÍTICAS>
<MODO_RESPUESTA>
<EXPLICACIÓN>
En tu respuesta debes:
Ser breve y directa: Proporciona la información en un formato claro y conciso, enfocándote en los pasos esenciales o la acción principal que debe tomarse.
Ser accionable: Prioriza el detalle suficiente para que el agente pueda transmitir la solución al afiliado rápidamente o profundizar si es necesario.

Evitar información innecesaria: Incluye solo los datos más relevantes para resolver la consulta. Si hay pasos opcionales o detalles adicionales, indícalos solo si son críticos.
Estructura breve: Usa puntos clave, numeración o listas de una sola línea si es necesario.

</EXPLICACION> 
   <EJEMPLO_MODO_RESPUESTA>
      <PREGUNTA>
         ¿Cómo tramitar la insulina tipo glargina?
      </PREGUNTA>
      <RESPUESTA>
         PAMI cubre al 100% la insulina tipo Glargina para casos especiales, previa autorización por vía de excepción. Para gestionarla, se debe presentar el Formulario de Insulinas por Vía de Excepción (INICIO o RENOVACIÓN) firmado por el médico especialista, acompañado de los últimos dos análisis de sangre completos (hemoglobina glicosilada y glucemia, firmados por un bioquímico), DNI, credencial de afiliación y receta electrónica. La solicitud se presenta en la UGL o agencia de PAMI y será evaluada por Nivel Central en un plazo de 72 horas. La autorización tiene una vigencia de 12 meses.
      </RESPUESTA>
   </EJEMPLO_MODO_RESPUESTA>
</MODO_RESPUESTA>

<CASOS_DE_PREGUNTA_RESPUESTA>
        <REQUISITOS>
        Si la respuesta tiene requisitos listar **TODOS** los requisitos encontrados en el contexto no omitas      incluso si aparecen en chunks distintos o al final de un fragmento. 
**Ejemplo crítico**: Si un chunk menciona "DNI, recibo, credencial" y otro agrega "Boleta de luz ", DEBEN incluirse ambos.
                             
         **Advertencia**:
          Si faltan requisitos del contexto en tu respuesta, se considerará ERROR GRAVE.                         
        </REQUISITOS>
       
   <IMPORTANTES_Y_EXCEPCIONES>
      Si los servicios o trámites tienen EXCEPCIONES, aclaraciones o detalles IMPORTANTES, EXCLUSIONES, menciónalos en tu respuesta.
        <EJEMPLO>
           ### Exclusiones:
            Afiliados internados en geriaticos privados
           ### Importante
            La orden tiene un vencimiento de 90 dias
           ### Excepciones
            Las solicitudes por vulnerabilidad no tendrán vencimiento
        </EJEMPLO>                      
   </IMPORTANTES_Y_EXCEPCIONES>

   <TRAMITES_NO_DISPONIBLES>
      <EXPLICACION>
         Si la pregunta es sobre un trámite o servicio que no está explícitamente indicado en la base de datos vectorial, menciona que no existe ese trámite o servicio.
      </EXPLICACION>
      <EJEMPLO>
         <PREGUNTA>
            ¿Cómo puede un afiliado solicitar un descuento por anteojos?
         </PREGUNTA>
         <RESPUESTA>
            PAMI no brinda un descuento por anteojos,Por lo tanto, si el afiliado decide comprar los anteojos por fuera de la red de ópticas de PAMI, no será posible solicitar un reintegro.
         </RESPUESTA>
      </EJEMPLO>
   </TRAMITES_NO_DISPONIBLES>

   <CALCULOS_NUMERICOS>
      <EXPLICACION>
         Si la pregunta involucra un cálculo o comparación numérica, evalúa aritméticamente para responderla.
      </EXPLICACION>
      <EJEMPLO>
         - Si se dice "menor a 10", es un número entre 1 y 9.
         - Si se dice "23", es un número entre 21 y 24.
      </EJEMPLO>
   </CALCULOS_NUMERICOS>

   <FORMATO_RESPUESTA>
      <EXPLICACION>
         Presenta la información en formato de lista Markdown si es necesario.
      </EXPLICACION>
   </FORMATO_RESPUESTA>

   <REFERENCIAS>
      <EXPLICACION>
         Al final de tu respuesta, incluye siempre un apartado titulado **Referencias** que contenga combinaciones únicas de **ID_SUB** y **SUBTIPO**, más un link con la siguiente estructura:
      </EXPLICACION>
      <EJEMPLO>
         Referencias:
         - ID_SUB = 347 | SUBTIPO = 'Traslados Programados'
         - LINK = https://simap.pami.org.ar/subtipo_detalle.php?id_sub=347
      </EJEMPLO>
   </REFERENCIAS>
</CASOS_DE_PREGUNTA_RESPUESTA>
"""

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
            
            system_message_content = SISTEMA_PROMPT_BASE + docs_content
       
            # Validar si excede el límite de palabras
            es_valido, num_palabras = validar_palabras(system_message_content)
            log_message(f"Sistema message contiene {num_palabras} palabras. Válido: {es_valido}")
            
            if not es_valido:
                # Reducir el contenido si es necesario
                system_message_content = reducir_contenido_por_palabras(SISTEMA_PROMPT_BASE + docs_content) # Asegurarse que se usa la base + docs para reducir
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
            log_message(f"Tiempo total de procesamiento: {processing_time:.2f} segundos")
            
            # CÁLCULO ÚNICO DE TOKENS - Hacerlo una sola vez aquí
            # 1. Tokens de la pregunta del usuario
            tokens_pregunta_usuario = contar_tokens(question_with_context, model_name)
            log_message(f"Tokens de la pregunta del usuario (question_with_context): {tokens_pregunta_usuario}")

            # 2. Tokens del prompt base del sistema
            tokens_prompt_sistema_base = contar_tokens(SISTEMA_PROMPT_BASE, model_name)
            log_message(f"Tokens del prompt base del sistema (SISTEMA_PROMPT_BASE): {tokens_prompt_sistema_base}")

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
                    "input_tokens": tokens_entrada,  # Incluir en metadata
                    "output_tokens": tokens_salida,  # Incluir en metadata
                    "total_tokens": tokens_entrada + tokens_salida,  # Incluir en metadata
                    "id_usuario": id_usuario if id_usuario is not None else 321,
                    "ugel_origen": ugel_origen if ugel_origen is not None else "Formosa"
                }
            }
            
        except Exception as e:
            log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}", level="ERROR")
            log_message(traceback.format_exc(), level="ERROR")
            
            # Calcular tiempo de procesamiento
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0
            tiempo_respuesta_ms = int(processing_time * 1000)
            
            # Preparar mensaje de error
            error_message = f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
            response_content = "Lo siento, ocurrió un error en el servidor. Por favor, intenta nuevamente más tarde."
            
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
            # Si el error ocurre antes del nodo 'generate', SISTEMA_PROMPT_BASE y docs_content_final no se habrían usado.
            # El `token_summary` ya usa los tokens que se le pasan, así que el log será coherente.

            # Se usa la constante global SISTEMA_PROMPT_BASE para el cálculo en caso de error
            tokens_prompt_sistema_base_error = contar_tokens(SISTEMA_PROMPT_BASE, model_name) 
            # tokens_entrada_error += tokens_prompt_sistema_base_error # Decidir si sumarlo
            # log_message(f"Tokens del prompt base del sistema (en error): {tokens_prompt_sistema_base_error}")

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
                    "ugel_origen": ugel_origen if ugel_origen is not None else "Formosa"
                }
            }
    
    except Exception as e:
        log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}", level="ERROR")
        log_message(traceback.format_exc(), level="ERROR")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
