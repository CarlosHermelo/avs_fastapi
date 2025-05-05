# app/services/graph_logic.py
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.token_utils import contar_tokens, validar_palabras, reducir_contenido_por_palabras
from app.core.logging_config import log_message
from app.core.config import qdrant_url, collection_name_fragmento, model_name

def build_graph(question, fecha_desde=None, fecha_hasta=None, k=None, api_key=None):
    """
    Construye un grafo de LangGraph para procesar preguntas sobre PAMI usando Qdrant
    
    Args:
        question (str): La pregunta a procesar
        fecha_desde (str, optional): Fecha de inicio para filtrado
        fecha_hasta (str, optional): Fecha de fin para filtrado
        k (int, optional): Número de documentos a recuperar
        api_key (str, optional): API key de OpenAI
        
    Returns:
        tuple: (graph, human_message)
    """
    # Clase para mantener estadísticas
    class RetrieveStats:
        def __init__(self):
            self.document_count = 0
    
    retrieve_stats = RetrieveStats()
    
    # Inicializar embeddings
    embeddings = OpenAIEmbeddings(api_key=api_key)
    
    # Inicializar el cliente de Qdrant
    qdrant_client = QdrantClient(url=qdrant_url)
    
    # Crear objeto Qdrant para búsqueda vectorial
    vector_store = Qdrant(
        client=qdrant_client,
        collection_name=collection_name_fragmento,
        embeddings=embeddings
    )
    
    # Inicializar el modelo LLM
    llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
    
    # Función de retrieve
    def retrieve(query: str):
        """Recuperar información relacionada con la consulta usando Qdrant."""
        log_message(f"########### RETRIEVE (Qdrant Graph) --------#####################")
        
        # Contar tokens de la consulta
        tokens_consulta = contar_tokens(query, model_name)
        log_message(f"Tokens de entrada en retrieve (consulta): {tokens_consulta}")
        
        # Usar valor k especificado o el valor por defecto
        k_value = k if k else 5
        
        # Realizar búsqueda en Qdrant
        try:
            retrieved_docs = vector_store.similarity_search_with_score(query, k=k_value)
            documentos_relevantes = [doc for doc, score in retrieved_docs]
            cantidad_fragmentos = len(documentos_relevantes)
            
            # Guardar la cantidad de fragmentos
            retrieve_stats.document_count = cantidad_fragmentos
            
            if not documentos_relevantes:
                log_message("No se encontró información suficiente para responder la pregunta.")
                return "Lo siento, no tengo información suficiente para responder esa pregunta."
            
            serialized = "\n\n".join(
                (f"fFRAGMENTO{doc.page_content}\nMETADATA{doc.metadata}") for doc in documentos_relevantes
            )
            
            # Contar tokens de la respuesta de retrieve
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
        
        # Contar tokens de entrada
        prompt_text = "\n".join([msg.content for msg in state["messages"]])
        tokens_entrada_qor = contar_tokens(prompt_text, model_name)
        log_message(f"Tokens de entrada en query_or_respond: {tokens_entrada_qor}")
        
        llm_with_tools = llm.bind_tools([retrieve])
        response = llm_with_tools.invoke(state["messages"])
        
        # Contar tokens de salida
        tokens_salida_qor = contar_tokens(response.content, model_name)
        log_message(f"Tokens de salida en query_or_respond: {tokens_salida_qor}")
        
        return {"messages": [response]}
    
    # Nodo 2: Ejecutar la herramienta de recuperación
    tools = ToolNode([retrieve])
    
    # Nodo 3: Generar la respuesta final
    def generate(state: MessagesState):
        """Genera la respuesta final usando los documentos recuperados."""
        log_message(f"###########GENERATE---------#####################")
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
            log_message(f"Se ha reducido el contenido a {len(system_message_content.split())} palabras.")
        
        prompt = [SystemMessage(content=system_message_content)] + [
            msg for msg in state["messages"] if msg.type in ("human", "system")
        ]
        
        # Contar tokens del prompt de entrada
        prompt_text = system_message_content + "\n" + "\n".join([msg.content for msg in state["messages"] if msg.type in ("human", "system")])
        tokens_entrada = contar_tokens(prompt_text, model_name)
        log_message(f"Tokens de entrada (prompt): {tokens_entrada}")
        
        # Realizar la inferencia
        response = llm.invoke(prompt)
        
        # Contar tokens de la respuesta
        tokens_salida = contar_tokens(response.content, model_name)
        log_message(f"Tokens de salida (respuesta): {tokens_salida}")
        log_message(f"Total tokens consumidos: {tokens_entrada + tokens_salida}")
        
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
    
    # Construir mensaje con contexto incluido
    question_with_context = f"""
Pregunta: {question}
"""
    if fecha_desde and fecha_hasta:
        question_with_context += f"Periodo: desde {fecha_desde} hasta {fecha_hasta}\n"
    
    # Preparar el mensaje para el grafo
    human_message = HumanMessage(content=question_with_context)
    
    return graph, human_message

