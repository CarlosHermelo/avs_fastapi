# app/services/graph_logic.py
from langgraph.graph import MessagesState, StateGraph
from app.services.retrieval import retrieve
from app.core.logging_config import log_message
from langchain_openai import ChatOpenAI
from app.core.config import model_name
import traceback
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

llm = ChatOpenAI(model=model_name, temperature=0)

def query_or_respond(state: MessagesState):
    print("[DEBUG-GRAPH] Iniciando nodo query_or_respond")
    print(f"[DEBUG-GRAPH] Estado actual: {state}")
    
    try:
        messages = state["messages"]
        print(f"[DEBUG-GRAPH] Mensajes recibidos: {messages}")
        
        # Verificar si hay mensajes y obtener el último mensaje
        if not messages:
            print("[DEBUG-GRAPH] No hay mensajes en el estado")
            return state
            
        last_message = messages[-1]
        print(f"[DEBUG-GRAPH] Último mensaje: {last_message}")
        
        # Verificar si el último mensaje es del usuario
        if hasattr(last_message, 'role') and last_message.role == "user":
            user_query = last_message.content
            print(f"[DEBUG-GRAPH] Consulta del usuario: {user_query}")
            
            # Recuperar documentos relevantes
            try:
                print("[DEBUG-GRAPH] Intentando recuperar documentos relevantes...")
                # Obtener k del config si está disponible
                k = 4  # valor por defecto
                if hasattr(state, "config") and state["config"] and "k" in state["config"]:
                    k = state["config"]["k"]
                    print(f"[DEBUG-GRAPH] Usando k={k} de la configuración")
                
                docs = retrieve(user_query, k=k)
                print(f"[DEBUG-GRAPH] Documentos recuperados: {len(docs)} docs")
                
                # Construir contexto con los documentos recuperados
                context_parts = []
                for i, doc in enumerate(docs):
                    context_parts.append(f"Documento {i+1}:\n{doc.page_content}")
                    if hasattr(doc, 'metadata') and doc.metadata:
                        context_parts.append(f"Metadata: {doc.metadata}")
                
                context = "\n\n".join(context_parts)
                print(f"[DEBUG-GRAPH] Contexto construido de {len(context)} caracteres")
                
                # Simulamos la llamada al retrieve para mantener la compatibilidad con el código original
                tool_inputs = {"query": user_query, "k": k}
                result_message = ToolMessage(
                    content=context,
                    tool_call_id="retrieve_call",
                    name="retrieve"
                )
                
                # Devolvemos el mensaje con el resultado del retrieve
                new_messages = messages.copy() + [result_message]
                return {"messages": new_messages}
                
            except Exception as e:
                print(f"[DEBUG-GRAPH] Error al recuperar documentos: {str(e)}")
                print(f"[DEBUG-GRAPH] Detalles del error: {traceback.format_exc()}")
                
                # En caso de error en la recuperación, pasamos al nodo generate sin contexto adicional
                return {"messages": messages}
        
        # Si no hay consulta del usuario o no es usuario, continuamos con los mensajes originales
        return {"messages": messages}
        
    except Exception as e:
        print(f"[DEBUG-GRAPH] Error en query_or_respond: {str(e)}")
        print(f"[DEBUG-GRAPH] Detalles del error: {traceback.format_exc()}")
        return state

def generate(state: MessagesState):
    print("[DEBUG-GRAPH] Iniciando nodo generate")
    print(f"[DEBUG-GRAPH] Estado actual: {state}")
    
    try:
        # Obtener mensajes del estado
        messages = state["messages"]
        print(f"[DEBUG-GRAPH] Cantidad de mensajes: {len(messages)}")
        
        # Extraer mensajes de herramienta (documentos recuperados)
        tool_messages = [msg for msg in messages if hasattr(msg, 'type') and msg.type == "tool"]
        print(f"[DEBUG-GRAPH] Mensajes de herramienta encontrados: {len(tool_messages)}")
        
        # Preparar el contexto con los documentos recuperados
        docs_content = ""
        if tool_messages:
            docs_content = "\n\n".join(msg.content for msg in tool_messages)
            print(f"[DEBUG-GRAPH] Contenido de documentos recuperado: {len(docs_content)} caracteres")
        
        # Creamos el mensaje del sistema con el contexto y las instrucciones
        system_message_content = f"""
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
- Si no existe una afirmación explícita, clara y literal en el contexto, responde exactamente: **"No tengo la información suficiente del SIMAP para responderte en forma precisa tu pregunta."**
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

<DATOS_RECUPERADOS>
{docs_content}
</DATOS_RECUPERADOS>
"""
        
        print("[DEBUG-GRAPH] Llamando al modelo LLM para generar respuesta...")
        
        # Filtrar mensajes de usuario para el prompt
        user_messages = [msg for msg in messages if hasattr(msg, 'role') and msg.role == "user"]
        
        # Convertir a formato de LangChain
        langchain_messages = [SystemMessage(content=system_message_content)]
        for msg in user_messages:
            langchain_messages.append(HumanMessage(content=msg.content))
            
        print(f"[DEBUG-GRAPH] Mensaje final para LLM: {len(langchain_messages)} mensajes")
        
        # Llamar al modelo LLM para obtener respuesta
        response = llm.invoke(langchain_messages)
        
        # Extraer la respuesta
        response_text = response.content
        print(f"[DEBUG-GRAPH] Respuesta generada por LLM: {response_text}")
        
        # Agregar la respuesta al estado como mensaje del asistente
        new_message = AIMessage(content=response_text)
        new_messages = messages.copy() + [new_message]
        
        return {"messages": new_messages}
    except Exception as e:
        print(f"[DEBUG-GRAPH] Error en generate: {str(e)}")
        print(f"[DEBUG-GRAPH] Detalles del error: {traceback.format_exc()}")
        
        # En caso de error, devolver una respuesta de fallback
        error_response = "Lo siento, hubo un problema al generar la respuesta. Por favor, inténtelo de nuevo."
        error_message = AIMessage(content=error_response)
        new_messages = messages.copy() + [error_message]
        
        return {"messages": new_messages}

def build_graph():
    print("[DEBUG-GRAPH] Iniciando construcción del grafo")
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(generate)
    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_edge("query_or_respond", "generate")
    print("[DEBUG-GRAPH] Grafo construido correctamente")
    return graph_builder.compile()

