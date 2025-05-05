# app/services/process_question.py
from app.services.graph_logic import build_graph
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
from app.core.config import model_name, max_results
from app.core.logging_config import get_logger
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store, get_llm
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# Obtener el logger
logger = get_logger()

# Crear una clase para mantener el estado de los fragmentos recuperados
class RetrieveStats:
    def __init__(self):
        self.document_count = 0
        self.last_fragments_count = 0

# Instanciar la clase RetrieveStats globalmente
retrieve_stats = RetrieveStats()

def process_question(question, fecha_desde=None, fecha_hasta=None, k=None):
    """
    Procesa una pregunta utilizando la base de datos vectorial Qdrant y
    devuelve una respuesta generada por un modelo de lenguaje.
    
    Args:
        question (str): La pregunta del usuario
        fecha_desde (str, optional): Fecha desde la cual filtrar resultados
        fecha_hasta (str, optional): Fecha hasta la cual filtrar resultados
        k (int, optional): Número máximo de documentos a recuperar
        
    Returns:
        str: La respuesta generada
    """
    try:
        # Línea divisoria para mejor visualización en logs
        logger.info("="*80)
        logger.info(f"##############-------INICIO PROCESS_QUESTION----------#####################")
        
        # Inicializar contadores
        retrieve_stats.document_count = 0
        
        # Registrar inicio del procesamiento con timestamp
        start_time = datetime.datetime.now()
        logger.info(f"[{start_time}] Procesando pregunta: {question}")
        
        # Obtener recursos desde las dependencias singleton
        embeddings = get_embeddings()
        qdrant_client = get_qdrant_client()
        vector_store = get_vector_store()
        llm = get_llm()
        
        # Determinar valor k (número de documentos a recuperar)
        if k is None:
            k = max_results  # Valor por defecto desde config
        else:
            k = int(k)
        
        # Función de retrieve adaptada para Qdrant
        def retrieve(query: str):
            """Recuperar información relacionada con la consulta usando Qdrant."""
            logger.info(f"########### RETRIEVE (Qdrant) --------#####################")
            
            # Contamos tokens de la consulta
            tokens_consulta = contar_tokens(query, model_name)
            logger.info(f"Tokens de entrada en retrieve (consulta): {tokens_consulta}")
            
            # Usar valor k proporcionado
            k_value = k
            logger.info(f"Buscando documentos relevantes con k={k_value}")
            
            # Realizar búsqueda en Qdrant
            try:
                retrieved_docs = vector_store.similarity_search_with_score(query, k=k_value)
                documentos_relevantes = [doc for doc, score in retrieved_docs]
                cantidad_fragmentos = len(documentos_relevantes)
                
                # Guardamos la cantidad de fragmentos
                retrieve_stats.document_count = cantidad_fragmentos
                retrieve_stats.last_fragments_count = cantidad_fragmentos
                
                if not documentos_relevantes:
                    logger.info("No se encontró información suficiente para responder la pregunta.")
                    return "Lo siento, no tengo información suficiente para responder esa pregunta."
                
                # Formato detallado para el log
                formatted_docs = "\n\n".join(
                    (f"FRAGMENTO #{i+1}: {doc.page_content}\nMETADATA: {doc.metadata}\nSCORE: {score}")
                    for i, (doc, score) in enumerate(retrieved_docs)
                )
                logger.info(f"Documentos recuperados:\n{formatted_docs}")
                
                serialized = "\n\n".join(
                    (f"fFRAGMENTO{doc.page_content}\nMETADATA{doc.metadata}") for doc in documentos_relevantes
                )
                
                # Contamos tokens de la respuesta de retrieve
                tokens_respuesta_retrieve = contar_tokens(serialized, model_name)
                logger.info(f"Fragmentos recuperados de Qdrant: {cantidad_fragmentos}")
                logger.info(f"Tokens de salida en retrieve: {tokens_respuesta_retrieve}")
                logger.info(f"Total tokens en retrieve: {tokens_consulta + tokens_respuesta_retrieve}")
                
                # Log del contenido completo recuperado (como en versión Chroma)
                logger.info(f"WEB-RETREIVE----> :\n {serialized} \n----------END-WEB-RETRIEBE <")
                
                return serialized
            except Exception as e:
                error_msg = f"Error al realizar la búsqueda en Qdrant: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                return "Error al buscar en la base de datos: no se pudo recuperar información relevante."
        
        # Nodo 1: Generar consulta o responder directamente
        def query_or_respond(state: MessagesState):
            """Genera una consulta para la herramienta de recuperación o responde directamente."""
            logger.info(f"########### QUERY OR RESPOND ---------#####################")
            
            # Contamos tokens de entrada
            prompt_text = "\n".join([msg.content for msg in state["messages"]])
            tokens_entrada_qor = contar_tokens(prompt_text, model_name)
            logger.info(f"Tokens de entrada en query_or_respond: {tokens_entrada_qor}")
            
            # Log del mensaje completo
            logger.info(f"Estado de mensajes entrante: {state}")
            
            llm_with_tools = llm.bind_tools([retrieve])
            response = llm_with_tools.invoke(state["messages"])
            
            # Contamos tokens de salida
            tokens_salida_qor = contar_tokens(response.content, model_name)
            logger.info(f"Tokens de salida en query_or_respond: {tokens_salida_qor}")
            logger.info(f"Total tokens en query_or_respond: {tokens_entrada_qor + tokens_salida_qor}")
            
            # Log de la respuesta completa
            logger.info(f"Respuesta de query_or_respond: {response.content}")
            
            return {"messages": [response]}
        
        # Nodo 2: Ejecutar la herramienta de recuperación
        tools = ToolNode([retrieve])
        
        # Nodo 3: Generar la respuesta final
        def generate(state: MessagesState):
            """Genera la respuesta final usando los documentos recuperados."""
            logger.info(f"###########WEB-generate---------#####################")
            
            # Extraer mensajes de herramienta recientes
            recent_tool_messages = [msg for msg in reversed(state["messages"]) if msg.type == "tool"]
            logger.info(f"Mensajes de herramienta encontrados: {len(recent_tool_messages)}")
            
            docs_content = "\n\n".join(doc.content for doc in recent_tool_messages[::-1])
            
            # Log del contenido de documentos
            logger.info(f"Contenido de documentos compilados:\n{docs_content[:1000]}... (truncado)")
            
            # Validar si los documentos contienen términos clave de la pregunta
            user_question = state["messages"][0].content.lower()
            terms = user_question.split()
            
            logger.info(f"Términos de búsqueda de la pregunta: {terms}")
            
            if not any(term in docs_content.lower() for term in terms):
                logger.info("No se encontraron términos de la pregunta en los documentos, enviando respuesta genérica.")
                return {"messages": [{"role": "assistant", "content": "Lo siento, no tengo información suficiente para responder esa pregunta."}]}
            
            system_message_content = ( """
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
""" + docs_content)
       
            # Validar si excede el límite de palabras
            es_valido, num_palabras = validar_palabras(system_message_content)
            logger.info(f"Sistema message contiene {num_palabras} palabras. Válido: {es_valido}")
            
            if not es_valido:
                # Reducir el contenido si es necesario
                system_message_content = reducir_contenido_por_palabras(system_message_content)
                logger.info(f"Se ha reducido el contenido a {count_words(system_message_content)} palabras.")
                logger.info(f"WEB-CONTEXTO_QUEDO RESUMIDO ASI (system_message_content\n): {system_message_content[:1000]}... (truncado)")
            
            prompt = [SystemMessage(content=system_message_content)] + [
                msg for msg in state["messages"] if msg.type in ("human", "system")
            ]
            
            # Log del prompt completo
            logger.info(f"WEB-PROMPT PROMPT ------>\n {prompt}--<")
            
            # Contamos tokens del prompt de entrada
            prompt_text = system_message_content + "\n" + "\n".join([msg.content for msg in state["messages"] if msg.type in ("human", "system")])
            tokens_entrada = contar_tokens(prompt_text, model_name)
            logger.info(f"Tokens de entrada (prompt): {tokens_entrada}")
            
            # Realizamos la inferencia
            logger.info(f"Generando respuesta final con modelo {model_name}")
            response = llm.invoke(prompt)
            
            # Contamos tokens de la respuesta
            tokens_salida = contar_tokens(response.content, model_name)
            logger.info(f"Tokens de entrada (respuesta) DE PREGUNTA:: {tokens_entrada}")
            logger.info(f"Tokens de salida (respuesta) DE PREGUNTA:: {tokens_salida}")
            logger.info(f"Total tokens consumidos DE PREGUNTA: {tokens_entrada + tokens_salida}")
            
            # Log de la respuesta completa
            logger.info(f"WEB-PROMPT RESPONSE ------>\n {response}--<")
            
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
        logger.info(f"##############-------PROCESANDO PROCESS_QUESTION----------#####################")
        
        # Preparar el mensaje con la pregunta y contexto
        question_with_context = f"""
Pregunta: {question}
Periodo: desde {fecha_desde} hasta {fecha_hasta}
"""
        
        # Registramos tokens de la pregunta inicial
        tokens_pregunta = contar_tokens(question_with_context, model_name)
        logger.info(f"Tokens de la pregunta inicial: {tokens_pregunta}")
        logger.info(f"Pregunta con contexto: {question_with_context}")
        
        # Preparar el mensaje para el grafo
        human_message = HumanMessage(content=question_with_context)
        
        # Iniciar el streaming del grafo
        response_content = None
        tokens_totales_entrada = tokens_pregunta
        tokens_totales_salida = 0
        
        try:
            # Diccionario para registrar tokens por cada nodo
            tokens_por_nodo = {
                "query_or_respond": {"entrada": 0, "salida": 0},
                "tools": {"entrada": 0, "salida": 0},
                "generate": {"entrada": 0, "salida": 0}
            }
            
            logger.info(f"Iniciando ejecución del grafo LangGraph...")
            
            last_step = None
            step_count = 0
            for step in graph.stream(
                {"messages": [human_message]},
                stream_mode="values",
                config={"configurable": {"thread_id": "user_question"}}
            ):
                step_count += 1
                last_step = step
                logger.info(f"Ejecutando paso {step_count} del grafo...")
                
                # Si hay mensajes y el último es del asistente, extraemos la respuesta
                if "messages" in step and step["messages"]:
                    assistant_messages = [msg for msg in step["messages"] 
                                        if hasattr(msg, 'type') and msg.type == "ai" or
                                            hasattr(msg, 'role') and msg.role == "assistant"]
                    
                    if assistant_messages:
                        latest_assistant_msg = assistant_messages[-1]
                        if hasattr(latest_assistant_msg, 'content'):
                            response_content = latest_assistant_msg.content
                            logger.info(f"Respuesta parcial actualizada en paso {step_count}")
            
            logger.info(f"Grafo completado con {step_count} pasos.")
            
            # Si no tenemos respuesta pero tenemos último paso
            if response_content is None and last_step and "messages" in last_step:
                logger.info("No se encontró respuesta en el streaming, buscando en el último paso...")
                for msg in reversed(last_step["messages"]):
                    if (hasattr(msg, 'type') and msg.type == "ai") or \
                    (hasattr(msg, 'role') and msg.role == "assistant"):
                        response_content = msg.content
                        logger.info("Respuesta encontrada en el último paso")
                        break
            
            # Si aún no hay respuesta
            if response_content is None:
                logger.info("No se pudo extraer ninguna respuesta del grafo. Usando respuesta genérica.")
                response_content = "Lo siento, no se pudo generar una respuesta."
            
            # Registrar resultado
            logger.info(f"Respuesta final generada, longitud: {len(response_content)}")
            
            # Calcular tiempo total y registrar resumen
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info(f"Tiempo total de procesamiento: {processing_time:.2f} segundos")
            
            # Calcular y registrar tokens totales
            tokens_respuesta = contar_tokens(response_content, model_name)
            logger.info(f"Tokens totales de entrada: {tokens_totales_entrada}")
            logger.info(f"Tokens totales de salida: {tokens_respuesta}")
            logger.info(f"Total general de tokens: {tokens_totales_entrada + tokens_respuesta}")
            
            # Registrar el resumen final
            log_token_summary(
                tokens_totales_entrada,
                tokens_respuesta,
                retrieve_stats.document_count,
                model_name
            )
            
            logger.info(f"##############-------FIN PROCESS_QUESTION----------#####################")
            logger.info("="*80)
            
            return response_content
            
        except Exception as e:
            error_msg = f"[ERROR] Error en el procesamiento del grafo: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return "Lo siento, ocurrió un error al procesar tu pregunta. Por favor, inténtalo de nuevo más tarde."
    
    except Exception as e:
        error_msg = f"Error al procesar la pregunta: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return "Lo siento, ocurrió un error al procesar tu pregunta. Por favor, inténtalo de nuevo más tarde."

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

