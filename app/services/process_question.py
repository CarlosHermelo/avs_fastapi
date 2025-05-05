# app/services/process_question.py
from app.services.graph_logic import build_graph
from app.services.token_utils import contar_tokens
from app.core.logging_config import log_message
import traceback
from langchain_core.messages import HumanMessage, AIMessage
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

# Obtener el logger
logger = get_logger()

# Variable para llevar el conteo total de tokens por sesión
session_token_stats = {
    "input_tokens": 0,
    "output_tokens": 0,
    "fragments_count": 0
}

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
        
        # Reiniciar estadísticas de tokens para esta sesión
        session_token_stats["input_tokens"] = 0
        session_token_stats["output_tokens"] = 0
        session_token_stats["fragments_count"] = 0
        
        # Registrar inicio del procesamiento con timestamp
        start_time = datetime.datetime.now()
        logger.info(f"[{start_time}] Procesando pregunta: {question}")
        
        # Contar tokens de la pregunta inicial
        question_tokens = contar_tokens(question, model_name)
        session_token_stats["input_tokens"] += question_tokens
        logger.info(f"Tokens de la pregunta inicial: {question_tokens}")
        
        # Información sobre fechas y parámetros
        if fecha_desde or fecha_hasta:
            logger.info(f"Filtro de fechas: desde {fecha_desde} hasta {fecha_hasta}")
        
        # Obtener recursos desde las dependencias singleton
        embeddings = get_embeddings()
        qdrant_client = get_qdrant_client()
        vector_store = get_vector_store()
        
        # Determinar valor k (número de documentos a recuperar)
        if k is None:
            k = max_results  # Valor por defecto desde config
        else:
            k = int(k)
        
        # Buscar documentos relevantes - Log distintivo para esta sección
        logger.info(f"########### RETRIEVE (Qdrant) --------#####################")
        logger.info(f"Buscando documentos relevantes con k={k}")
        
        # Contar tokens de la búsqueda
        retrieval_input_tokens = contar_tokens(question, model_name)
        logger.info(f"Tokens de entrada en retrieve (consulta): {retrieval_input_tokens}")
        
        # Realizar la búsqueda
        retrieved_docs = vector_store.similarity_search_with_score(question, k=k)
        
        # Procesar resultados
        if not retrieved_docs:
            logger.warning("No se encontraron documentos relevantes.")
            return "No tengo la información suficiente del SIMAP para responderte en forma precisa tu pregunta."
        
        # Ordenar por score (menor score = mayor similitud)
        retrieved_docs.sort(key=lambda x: x[1])
        
        # Extraer documentos y formatear el contexto
        context = "\n\n".join([
            f"FRAGMENTO: {doc.page_content}\n" +
            f"METADATA: {doc.metadata}\n" +
            f"SCORE: {score}"
            for doc, score in retrieved_docs
        ])
        
        # Guardar estadísticas de fragmentos
        session_token_stats["fragments_count"] = len(retrieved_docs)
        
        # Log de contenido recuperado (similar a la versión Chroma)
        logger.info(f"Se encontraron {len(retrieved_docs)} documentos relevantes.")
        logger.info(f"WEB-RETREIVE----> :\n {context} \n----------END-WEB-RETRIEBE <")
        
        # Contar tokens del contexto
        context_tokens = contar_tokens(context, model_name)
        logger.info(f"Tokens del contexto: {context_tokens}")
        session_token_stats["input_tokens"] += context_tokens
        
        # Definir la plantilla para el prompt con el formato completo y detallado
        prompt_template = PromptTemplate.from_template(
            """
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
        Si la respuesta tiene requisitos listar **TODOS** los requisitos encontrados en el contexto no omitas incluso si aparecen en chunks distintos o al final de un fragmento. 
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

<DOCUMENTOS_RELEVANTES>
{context}
</DOCUMENTOS_RELEVANTES>

<PREGUNTA>
{question}
</PREGUNTA>

RESPUESTA:"""
        )
        
        # Preparar el prompt completo con los documentos relevantes
        prompt = prompt_template.format(context=context, question=question)
        
        # Contar tokens del prompt completo
        prompt_tokens = contar_tokens(prompt, model_name)
        logger.info(f"Tokens del prompt completo: {prompt_tokens}")
        session_token_stats["input_tokens"] = prompt_tokens  # Actualizar con valor más preciso
        
        # Obtener el modelo LLM desde las dependencias
        llm = get_llm()
        
        # Generar la respuesta - Log distintivo para esta sección
        logger.info(f"########### GENERATE (LLM) --------#####################")
        logger.info(f"Generando respuesta usando modelo {model_name}")
        
        response = llm.invoke(prompt)
        answer = response.content
        
        # Contar tokens de la respuesta
        answer_tokens = contar_tokens(answer, model_name)
        session_token_stats["output_tokens"] = answer_tokens
        logger.info(f"Tokens de la respuesta: {answer_tokens}")
        
        # Calcular tiempo total de procesamiento
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Tiempo total de procesamiento: {processing_time:.2f} segundos")
        
        # Generar resumen de tokens
        token_summary = log_token_summary(
            session_token_stats["input_tokens"],
            session_token_stats["output_tokens"],
            session_token_stats["fragments_count"],
            model_name
        )
        
        logger.info(f"##############-------FIN PROCESS_QUESTION----------#####################")
        logger.info("="*80)
        
        return answer
    
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
    
    # Guardar en formato JSON para análisis posterior (igual que en la versión Chroma)
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

