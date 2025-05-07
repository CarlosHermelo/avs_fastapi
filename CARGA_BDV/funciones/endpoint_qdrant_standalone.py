"""
Endpoint FastAPI standalone para usar Qdrant como base de datos vectorial
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_qdrant.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("endpoint_qdrant")

def log_message(message, level="INFO"):
    """Función simple para loguear mensajes"""
    if level == "INFO":
        logger.info(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.debug(message)

# Definición de modelos de datos
class QuestionRequest(BaseModel):
    question_input: str
    fecha_desde: str = "2023-01-01"
    fecha_hasta: str = "2024-12-31"
    k: int = 5

class AnswerResponse(BaseModel):
    answer: str

class CompleteAnalysisRequest(BaseModel):
    question_input: str
    fecha_desde: str = "2023-01-01"
    fecha_hasta: str = "2024-12-31"
    k: int = 5

class CompleteAnalysisResponse(BaseModel):
    answer: str
    metadata: dict = {}

# Cargar configuración
def cargar_config_qdrant():
    """Carga la configuración desde config.ini"""
    # Posibles ubicaciones del archivo config.ini
    posibles_rutas = [
        'config.ini',                   # En el directorio actual
        '../config.ini',                # En el directorio padre
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),  # En el mismo directorio
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')  # Directorio padre
    ]
    
    # Buscar el archivo en las posibles ubicaciones
    config_path = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            config_path = ruta
            break
    
    if not config_path:
        raise FileNotFoundError("No se pudo encontrar el archivo config.ini")
    
    # Cargar la configuración
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Obtener los valores de configuración
    qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
    collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store')
    model_name = config['DEFAULT'].get('modelo', 'gpt-3.5-turbo')
    
    return qdrant_url, collection_name, model_name

# Crear una clase para mantener el estado de los fragmentos recuperados
class RetrieveStats:
    def __init__(self):
        self.document_count = 0
        
retrieve_stats = RetrieveStats()

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
        "vector_db": "Qdrant"
    }
    
    log_message(f"RESUMEN_JSON: {json.dumps(resumen_json)}")
    log_message(separador)
    
    return resumen_json

# Función básica para procesar preguntas con Qdrant
def process_question(question, fecha_desde=None, fecha_hasta=None, k=None):
    """
    Procesa una pregunta utilizando la base de datos vectorial Qdrant y
    devuelve una respuesta generada por un modelo de lenguaje.
    """
    try:
        # Registrar inicio del procesamiento
        start_time = datetime.datetime.now()
        logger.info(f"Procesando pregunta: {question}")
        
        # Cargar configuración
        qdrant_url, collection_name, model_name = cargar_config_qdrant()
        
        # Inicializar embeddings
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        
        # Inicializar el cliente de Qdrant
        qdrant_client = QdrantClient(url=qdrant_url)
        
        # Verificar que la colección existe
        try:
            qdrant_client.get_collection(collection_name)
            logger.info(f"Colección {collection_name} encontrada en Qdrant.")
        except Exception as e:
            error_msg = f"Error: La colección {collection_name} no existe en Qdrant: {str(e)}"
            logger.error(error_msg)
            return "Lo siento, no puedo procesar tu pregunta en este momento debido a un error en la base de datos."
        
        # Crear objeto Qdrant para búsqueda vectorial
        vector_store = Qdrant(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings
        )
        
        # Determinar valor k (número de documentos a recuperar)
        if k is None:
            k = 4  # Valor por defecto
        else:
            k = int(k)
        
        # Buscar documentos relevantes
        logger.info(f"Buscando documentos relevantes con k={k}")
        retrieved_docs = vector_store.similarity_search_with_score(question, k=k)
        
        # Procesar resultados
        if not retrieved_docs:
            logger.warning("No se encontraron documentos relevantes.")
            return "No tengo la información suficiente del SIMAP para responderte en forma precisa tu pregunta."
        
        # Extraer documentos y formatear el contexto
        context = "\n\n".join([
            f"FRAGMENTO: {doc.page_content}\n" +
            f"METADATA: {doc.metadata}\n" +
            f"SCORE: {score}"
            for doc, score in retrieved_docs
        ])
        
        logger.info(f"Se encontraron {len(retrieved_docs)} documentos relevantes.")
        
        # Crear el prompt para el modelo
        prompt = f"""
<CONTEXTO>
La información proporcionada tiene como objetivo apoyar a los agentes que trabajan en las agencias de PAMI, 
quienes se encargan de atender las consultas de los afiliados.
</CONTEXTO>

<ROL>
Eres un asistente virtual experto en los servicios y trámites de PAMI.
</ROL>

<TAREA>
Tu tarea es responder preguntas relacionadas con lo trámites y servicios que ofrece la obra social PAMI,
basándote únicamente en los datos disponibles a continuación. Si la información no está disponible,
debes decir 'No tengo esa información en este momento'.
</TAREA>

<REGLAS_CRÍTICAS>
- **PROHIBIDO hacer inferencias, generalizaciones, deducciones o suposiciones sobre trámites, renovaciones, requisitos o períodos.**
- Si no existe una afirmación explícita, clara y literal en el contexto, responde exactamente: 
**"No tengo la informacion suficiente del SIMAP para responderte en forma precisa tu pregunta."**
- Cada afirmación incluida en tu respuesta debe tener respaldo textual directo en el contexto.
</REGLAS_CRÍTICAS>

<DOCUMENTOS_RELEVANTES>
{context}
</DOCUMENTOS_RELEVANTES>

<PREGUNTA>
{question}
</PREGUNTA>

RESPUESTA:
"""
        
        # Inicializar el modelo LLM
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=openai_api_key)
        
        # Generar respuesta
        logger.info(f"Generando respuesta con modelo {model_name}")
        llm_response = llm.invoke(prompt)
        answer = llm_response.content
        
        # Calcular tiempo total de procesamiento
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Respuesta generada en {processing_time:.2f} segundos")
        
        return answer
        
    except Exception as e:
        logger.error(f"Error al procesar la pregunta: {str(e)}", exc_info=True)
        return "Ha ocurrido un error al procesar tu pregunta. Por favor, inténtalo de nuevo más tarde."

# Inicializar la aplicación FastAPI
app = FastAPI(title="API PAMI con Qdrant", 
              description="API para consultas a la base de datos vectorial Qdrant",
              version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "API de PAMI con Qdrant funcionando. Usar /docs para ver la documentación."}

@app.post("/process_question", response_model=AnswerResponse)
def handle_question(request: QuestionRequest):
    """Endpoint simple para procesar preguntas"""
    log_message(f"[DEBUG-API] Recibida solicitud con datos: {request}")
    
    answer = process_question(
        request.question_input,
        request.fecha_desde,
        request.fecha_hasta,
        request.k
    )
    
    log_message(f"[DEBUG-API] Respuesta generada: {answer}")
    return {"answer": answer}

@app.post("/complete_analysis", response_model=CompleteAnalysisResponse)
async def handle_complete_analysis(request: CompleteAnalysisRequest):
    """
    Endpoint que integra todo el proceso de análisis de texto completo
    usando LangGraph y Qdrant
    """
    log_message(f"[DEBUG-COMPLETE] Recibida solicitud completa con datos: {request}")
    
    try:
        # Cargar configuración
        qdrant_url, collection_name, model_name = cargar_config_qdrant()
        
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
            log_message(f"Colección {collection_name} encontrada en Qdrant.")
        except Exception as e:
            error_msg = f"Error: La colección {collection_name} no existe en Qdrant: {str(e)}"
            log_message(error_msg, level='ERROR')
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Crear objeto Qdrant para búsqueda vectorial
        vector_store = Qdrant(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings
        )
        
        # Inicializar el modelo LLM
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=openai_api_key)
        
        # Función de retrieve adaptada para Qdrant
        def retrieve(query: str):
            """Recuperar información relacionada con la consulta usando Qdrant."""
            log_message(f"########### RETRIEVE (Qdrant) --------#####################")
            
            # Contamos tokens de la consulta
            tokens_consulta = contar_tokens(query, model_name)
            log_message(f"Tokens de entrada en retrieve (consulta): {tokens_consulta}")
            
            # Usar valor k del request
            k_value = request.k if request.k else 4
            
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
                
                serialized = "\n\n".join(
                    (f"fFRAGMENTO{doc.page_content}\nMETADATA{doc.metadata}") for doc in documentos_relevantes
                )
                
                # Contamos tokens de la respuesta de retrieve
                tokens_respuesta_retrieve = contar_tokens(serialized, model_name)
                log_message(f"Fragmentos recuperados de Qdrant: {cantidad_fragmentos}")
                log_message(f"Tokens de salida en retrieve: {tokens_respuesta_retrieve}")
                log_message(f"Total tokens en retrieve: {tokens_consulta + tokens_respuesta_retrieve}")
                
                return serialized
            except Exception as e:
                error_msg = f"Error al realizar la búsqueda en Qdrant: {str(e)}"
                log_message(error_msg, level='ERROR')
                return "Error al buscar en la base de datos: no se pudo recuperar información relevante."
        
        # Nodo 1: Generar consulta o responder directamente
        def query_or_respond(state: MessagesState):
            """Genera una consulta para la herramienta de recuperación o responde directamente."""
            log_message(f"########### QUERY OR RESPOND ---------#####################")
            
            # Contamos tokens de entrada
            prompt_text = "\n".join([msg.content for msg in state["messages"]])
            tokens_entrada_qor = contar_tokens(prompt_text, model_name)
            log_message(f"Tokens de entrada en query_or_respond: {tokens_entrada_qor}")
            
            llm_with_tools = llm.bind_tools([retrieve])
            response = llm_with_tools.invoke(state["messages"])
            
            # Contamos tokens de salida
            tokens_salida_qor = contar_tokens(response.content, model_name)
            log_message(f"Tokens de salida en query_or_respond: {tokens_salida_qor}")
            
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
La información proporcionada tiene como objetivo apoyar a los agentes que trabajan en las agencias de PAMI, 
quienes se encargan de atender las consultas de los afiliados.
</CONTEXTO>

<ROL>
 Eres un asistente virtual experto en los servicios y trámites de PAMI.
</ROL>

<TAREA>
   Tu tarea es responder preguntas relacionadas con lo trámites y servicios que ofrece la obra social PAMI, 
   basándote únicamente en los datos disponibles en la base de datos vectorial. 
   Si la información no está disponible, debes decir 'No tengo esa información en este momento'.
</TAREA>

<REGLAS_CRÍTICAS>
- **PROHIBIDO hacer inferencias, generalizaciones, deducciones o suposiciones sobre trámites, renovaciones, requisitos o períodos.**
- Si no existe una afirmación explícita, clara y literal en el contexto, responde exactamente: 
  **"No tengo la informacion suficiente del SIMAP para responderte en forma precisa tu pregunta."**
- Cada afirmación incluida en tu respuesta debe tener respaldo textual directo en el contexto.
</REGLAS_CRÍTICAS>
""" + docs_content)
            
            # Validar si excede el límite de palabras
            es_valido, num_palabras = validar_palabras(system_message_content)
            if not es_valido:
                # Reducir el contenido si es necesario
                system_message_content = reducir_contenido_por_palabras(system_message_content)
                log_message(f"Se ha reducido el contenido a {count_words(system_message_content)} palabras.")
            
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
            log_message(f"Tokens de salida (respuesta): {tokens_salida}")
            log_message(f"Total tokens consumidos: {tokens_entrada + tokens_salida}")
            
            # Añadimos un resumen del conteo de tokens
            log_token_summary(tokens_entrada, tokens_salida, model_name)
            
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
                    "vector_db": "Qdrant"
                }
            }
            
        except Exception as e:
            log_message(f"[ERROR-COMPLETE] Error procesando la solicitud: {str(e)}", level="ERROR")
            log_message(traceback.format_exc(), level="ERROR")
            raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    except Exception as e:
        log_message(f"[ERROR-GENERAL] Error inesperado: {str(e)}", level="ERROR")
        log_message(traceback.format_exc(), level="ERROR")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    # Para probar localmente
    print("Ejecuta este archivo con uvicorn: uvicorn endpoint_qdrant_standalone:app --host 0.0.0.0 --port 8000") 