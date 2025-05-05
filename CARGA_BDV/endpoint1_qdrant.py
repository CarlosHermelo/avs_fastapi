# app/api/endpoints.py
from fastapi import APIRouter, HTTPException
from app.models.schemas import QuestionRequest, AnswerResponse, CompleteAnalysisRequest, CompleteAnalysisResponse
from app.services.process_question import process_question
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
from app.core.config import model_name, collection_name_fragmento, fragment_store_directory
from app.core.logging_config import log_message

router = APIRouter()

# Función para cargar configuración específica de Qdrant
def cargar_config_qdrant():
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Cargar configuración de SERVICIOS_SIMAP_Q
    qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
    collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store')
    
    return qdrant_url, collection_name

@router.post("/process_question", response_model=AnswerResponse)
def handle_question(request: QuestionRequest):
    print(f"[DEBUG-API] Recibida solicitud con datos: {request}")
    print(f"[DEBUG-API] Pregunta: {request.question_input}")
    print(f"[DEBUG-API] Fecha desde: {request.fecha_desde}")
    print(f"[DEBUG-API] Fecha hasta: {request.fecha_hasta}")
    print(f"[DEBUG-API] k: {request.k}")
    
    answer = process_question(
        request.question_input,
        request.fecha_desde,
        request.fecha_hasta,
        request.k
    )
    
    print(f"[DEBUG-API] Respuesta generada: {answer}")
    return {"answer": answer}

# Crear una clase para mantener el estado de los fragmentos recuperados
class RetrieveStats:
    def __init__(self):
        self.document_count = 0
        
retrieve_stats = RetrieveStats()

# Nuevo endpoint que integra todo el proceso en un solo archivo
@router.post("/complete_analysis", response_model=CompleteAnalysisResponse)
async def handle_complete_analysis(request: CompleteAnalysisRequest):
    """
    Endpoint que integra todo el proceso de análisis de texto completo
    adaptado para usar Qdrant como base de datos vectorial
    """
    print(f"[DEBUG-COMPLETE] Recibida solicitud completa con datos: {request}")
    
    try:
        # Cargar configuración de Qdrant
        qdrant_url, collection_name = cargar_config_qdrant()
        
        # Inicializar contador de documentos
        retrieve_stats.document_count = 0
        
        # Embeddings y conexión a Qdrant
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        
        # Inicializar cliente Qdrant
        qdrant_client = QdrantClient(url=qdrant_url)
        
        # Verificar que la colección existe
        try:
            qdrant_client.get_collection(collection_name)
            print(f"Colección {collection_name} encontrada en Qdrant.")
        except Exception as e:
            error_msg = f"Error: La colección {collection_name} no existe en Qdrant: {str(e)}"
            print(error_msg)
            log_message(error_msg, level='ERROR')
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Crear objeto Qdrant para búsqueda vectorial
        vector_store = Qdrant(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings
        )
        
        # Inicializar el modelo LLM
        llm = ChatOpenAI(model=model_name, temperature=0)
        
        # Crear función de retrieve adaptada para Qdrant
        def retrieve(query: str):
            """Recuperar información relacionada con la consulta usando Qdrant."""
            log_message(f"########### RETRIEVE (Qdrant) --------#####################")
            
            # Contamos tokens de la consulta
            tokens_consulta = contar_tokens(query, model_name)
            log_message(f"Tokens de entrada en retrieve (consulta): {tokens_consulta}")
            
            # Usar valor k del request o el valor por defecto
            k_value = request.k if request.k else 4
            
            # Realizar búsqueda en Qdrant
            try:
                retrieved_docs = vector_store.similarity_search_with_score(query, k=k_value)
                documentos_relevantes = [doc for doc, score in retrieved_docs]
                cantidad_fragmentos = len(documentos_relevantes)
                
                # Guardamos la cantidad de fragmentos en la variable global
                retrieve_stats.document_count = cantidad_fragmentos
                
                if not documentos_relevantes:
                    log_message("No se encontró información suficiente para responder la pregunta.")
                    return "Lo siento, no tengo información suficiente para responder esa pregunta."
                
                serialized = "\n\n".join(
                    (f"fFRAGMENTO{doc.page_content}\nMETADATA{doc.metadata}") for doc in documentos_relevantes
                )
                
                # Contamos tokens de la respuesta de retrieve
                tokens_respuesta_retrieve = contar_tokens(serialized, model_name)
                log_message(f"Fragmentos recuperados de la base de datos vectorial Qdrant: {cantidad_fragmentos}")
                log_message(f"Tokens de salida en retrieve (documentos): {tokens_respuesta_retrieve}")
                log_message(f"Total tokens en retrieve: {tokens_consulta + tokens_respuesta_retrieve}")
                
                log_message(f"WEB-RETREIVE----> :\n {serialized} \n----------END-WEB-RETRIEBE <")
                return serialized
            except Exception as e:
                error_msg = f"Error al realizar la búsqueda en Qdrant: {str(e)}"
                log_message(error_msg, level='ERROR')
                return "Error al buscar en la base de datos: no se pudo recuperar información relevante."
        
        # Nodo 1: Generar consulta o responder directamente
        def query_or_respond(state: MessagesState):
            """Genera una consulta para la herramienta de recuperación o responde directamente."""
            log_message(f"########### QUERY OR RESPOND ---------#####################")
            
            # Contamos tokens de entrada para query_or_respond
            prompt_text = "\n".join([msg.content for msg in state["messages"]])
            tokens_entrada_qor = contar_tokens(prompt_text, model_name)
            log_message(f"Tokens de entrada en query_or_respond: {tokens_entrada_qor}")
            
            llm_with_tools = llm.bind_tools([retrieve])
            response = llm_with_tools.invoke(state["messages"])
            
            # Contamos tokens de salida
            tokens_salida_qor = contar_tokens(response.content, model_name)
            log_message(f"Tokens de salida en query_or_respond: {tokens_salida_qor}")
            log_message(f"Total tokens en query_or_respond: {tokens_entrada_qor + tokens_salida_qor}")
            
            return {"messages": [response]}
        
        # Nodo 2: Ejecutar la herramienta de recuperación
        tools = ToolNode([retrieve])
        
        # Nodo 3: Generar la respuesta final
        def generate(state: MessagesState):
            """Genera la respuesta final usando los documentos recuperados."""
            log_message(f"###########WEB-generate---------#####################")
            recent_tool_messages = [msg for msg in reversed(state["messages"]) if msg.type == "tool"]
            docs_content = "\n\n".join(doc.content for doc in recent_tool_messages[::-1])
            
            # Validar si los documentos contienen términos clave de la pregunta
            user_question = state["messages"][0].content.lower()
            terms = user_question.split()
            
            if not any(term in docs_content.lower() for term in terms):
                return {"messages": [{"role": "assistant", "content": "Lo siento, no tengo información suficiente para responder esa pregunta."}]}
            
            system_message_content = ("""
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
            if not es_valido:
                # Reducir el contenido si es necesario
                system_message_content = reducir_contenido_por_palabras(system_message_content)
                log_message(f"###########WEB-Se ha reducido el contenido a {count_words(system_message_content)} palabras.")
            
            prompt = [SystemMessage(content=system_message_content)] + [
                msg for msg in state["messages"] if msg.type in ("human", "system")
            ]
            
            # Contamos tokens del prompt de entrada
            prompt_text = system_message_content + "\n" + "\n".join([msg.content for msg in state["messages"] if msg.type in ("human", "system")])
            tokens_entrada = contar_tokens(prompt_text, model_name)
            log_message(f"Tokens de entrada (prompt): {tokens_entrada}")
            
            # Realizamos la inferencia
            response = llm.invoke(prompt)
            
            # Contamos tokens de la respuesta
            tokens_salida = contar_tokens(response.content, model_name)
            log_message(f"Tokens de salida (respuesta) DE PREGUNTA:: {tokens_salida}")
            log_message(f"Total tokens consumidos DE PREGUNTA: {tokens_entrada + tokens_salida}")
            
            # Añadimos un resumen claro del conteo de tokens
            log_token_summary(tokens_entrada, tokens_salida, model_name)
            
            return {"messages": [response]}
        
        # Funciones auxiliares
        def contar_tokens(texto, modelo="gpt-3.5-turbo"):
            try:
                if modelo.startswith("gpt-4"):
                    codificador = tiktoken.encoding_for_model("gpt-4")
                elif modelo.startswith("gpt-3.5"):
                    codificador = tiktoken.encoding_for_model("gpt-3.5-turbo")
                else:
                    codificador = tiktoken.get_encoding("cl100k_base")
                
                tokens = len(codificador.encode(texto))
                return tokens
            except Exception as e:
                log_message(f"Error al contar tokens: {str(e)}", level='ERROR')
                return 0
        
        def count_words(text):
            return len(text.split())
        
        def validar_palabras(prompt, max_palabras=10000):
            num_palabras = count_words(prompt)
            if num_palabras > max_palabras:
                log_message(f"\nEl contenido supera el límite de {max_palabras} palabras ({num_palabras} palabras utilizadas).")
                return False, num_palabras
            return True, num_palabras
        
        def reducir_contenido_por_palabras(text, max_palabras=10000):
            palabras = text.split()
            if len(palabras) > max_palabras:
                log_message("El contenido es demasiado largo, truncando...")
                return " ".join(palabras[:max_palabras]) + "\n\n[Contenido truncado...]"
            return text
        
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
                "vector_db": "Qdrant"  # Añadido para diferenciar
            }
            
            log_message(f"RESUMEN_JSON: {json.dumps(resumen_json)}")
            log_message(separador)
            
            return resumen_json
        
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
        log_message(f"##############-------COMPLETE_ANALYSIS (Qdrant)----------#####################")
        
        # Construir mensaje con contexto incluido
        question_with_context = f"""
Pregunta: {request.question_input}
Periodo: desde {request.fecha_desde} hasta {request.fecha_hasta}
"""
        
        # Registramos tokens de la pregunta inicial
        tokens_pregunta = contar_tokens(question_with_context, model_name)
        log_message(f"Tokens de la pregunta inicial: {tokens_pregunta}")
        
        # Preparar el mensaje para el grafo
        human_message = HumanMessage(content=question_with_context)
        
        # Iniciar el streaming del grafo
        response_content = None
        token_summary = None
        
        try:
            # Iniciamos contadores
            tokens_totales_entrada = tokens_pregunta
            tokens_totales_salida = 0
            
            last_step = None
            for step in graph.stream(
                {"messages": [human_message]},
                stream_mode="values",
                config={"configurable": {"thread_id": "user_question"}}
            ):
                last_step = step
                
                # Si hay mensajes y el último es del asistente, extraemos la respuesta
                if "messages" in step and step["messages"]:
                    assistant_messages = [msg for msg in step["messages"] 
                                         if hasattr(msg, 'type') and msg.type == "ai" or
                                            hasattr(msg, 'role') and msg.role == "assistant"]
                    
                    if assistant_messages:
                        latest_assistant_msg = assistant_messages[-1]
                        if hasattr(latest_assistant_msg, 'content'):
                            response_content = latest_assistant_msg.content
            
            # Si no tenemos respuesta pero tenemos último paso
            if response_content is None and last_step and "messages" in last_step:
                for msg in reversed(last_step["messages"]):
                    if (hasattr(msg, 'type') and msg.type == "ai") or \
                       (hasattr(msg, 'role') and msg.role == "assistant"):
                        response_content = msg.content
                        break
            
            # Si aún no hay respuesta
            if response_content is None:
                response_content = "Lo siento, no se pudo generar una respuesta."
            
            # Registrar resultado
            log_message(f"##############-------FIN COMPLETE_ANALYSIS (Qdrant)----------#####################")
            
            # Crear respuesta
            return {
                "answer": response_content,
                "metadata": {
                    "document_count": retrieve_stats.document_count,
                    "model": model_name,
                    "question": request.question_input,
                    "fecha_desde": request.fecha_desde,
                    "fecha_hasta": request.fecha_hasta,
                    "vector_db": "Qdrant"  # Añadido para diferenciar
                }
            }
            
        except Exception as e:
            log_message(f"[ERROR-COMPLETE] Error procesando la solicitud: {str(e)}")
            log_message(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    except Exception as e:
        log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}")
        log_message(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") 