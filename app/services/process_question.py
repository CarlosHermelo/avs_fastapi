# app/services/process_question.py
from app.services.graph_logic import build_graph
from app.services.token_utils import contar_tokens
from app.core.logging_config import log_message
import traceback
from langchain_core.messages import HumanMessage, AIMessage

def process_question(question_input: str, fecha_desde: str, fecha_hasta: str, k: int):
    print(f"[DEBUG-PROCESS] Iniciando procesamiento de pregunta: {question_input}")
    print(f"[DEBUG-PROCESS] Parámetros: fecha_desde={fecha_desde}, fecha_hasta={fecha_hasta}, k={k}")
    
    try:
        print("[DEBUG-PROCESS] Construyendo grafo...")
        graph = build_graph()
        print("[DEBUG-PROCESS] Grafo construido correctamente")
        
        response = None
        
        # Construir mensaje con contexto incluido
        question_with_context = f"""
Pregunta: {question_input}
Periodo: desde {fecha_desde} hasta {fecha_hasta}
"""
        print(f"[DEBUG-PROCESS] Pregunta con contexto: {question_with_context}")
        
        # Crear mensaje de usuario usando langchain_core.messages
        user_message = HumanMessage(content=question_with_context)
        
        # Preparar datos de entrada para el grafo
        input_data = {
            "messages": [user_message],
            "config": {
                "k": k,
                "fecha_desde": fecha_desde, 
                "fecha_hasta": fecha_hasta
            }
        }
        print(f"[DEBUG-PROCESS] Datos de entrada al grafo: {input_data}")
        
        print("[DEBUG-PROCESS] Comenzando streaming del grafo...")
        try:
            last_step = None
            step_count = 0
            for step in graph.stream(
                input_data,
                stream_mode="values",
                config={"configurable": {"thread_id": "user_question", "k": k}},
            ):
                step_count += 1
                print(f"[DEBUG-PROCESS] Paso {step_count} del grafo")
                print(f"[DEBUG-PROCESS] Llaves en el step: {step.keys()}")
                
                # Guardar el último paso para extraer la respuesta final
                last_step = step
                
                # Si hay mensajes, extraer el último que sea del asistente
                if "messages" in step and step["messages"]:
                    assistant_messages = [msg for msg in step["messages"] 
                                         if hasattr(msg, 'type') and msg.type == "ai" or
                                            hasattr(msg, 'role') and msg.role == "assistant"]
                    
                    if assistant_messages:
                        latest_assistant_msg = assistant_messages[-1]
                        if hasattr(latest_assistant_msg, 'content'):
                            response = latest_assistant_msg.content
                            print(f"[DEBUG-PROCESS] Respuesta actual: {response}")
            
            # Si al final no tenemos respuesta pero tenemos un último paso, intentar extraerla
            if response is None and last_step and "messages" in last_step:
                print("[DEBUG-PROCESS] Intentando extraer respuesta final del último paso")
                for msg in reversed(last_step["messages"]):
                    if (hasattr(msg, 'type') and msg.type == "ai") or \
                       (hasattr(msg, 'role') and msg.role == "assistant"):
                        response = msg.content
                        print(f"[DEBUG-PROCESS] Respuesta final encontrada: {response}")
                        break
            
            # Si aún no tenemos respuesta, usar un mensaje predeterminado
            if response is None:
                response = "Lo siento, no se pudo generar una respuesta. Por favor, inténtelo de nuevo."
                print("[DEBUG-PROCESS] No se encontró respuesta en los mensajes del grafo")
                
        except Exception as e:
            print(f"[DEBUG-PROCESS] Error en el streaming del grafo: {str(e)}")
            print(f"[DEBUG-PROCESS] Detalles del error: {traceback.format_exc()}")
            return f"Error: {str(e)}"
        
        print(f"[DEBUG-PROCESS] Respuesta final: {response}")
        return response
    except Exception as e:
        print(f"[DEBUG-PROCESS] Error global: {str(e)}")
        print(f"[DEBUG-PROCESS] Detalles del error: {traceback.format_exc()}")
        return f"Error: {str(e)}"

