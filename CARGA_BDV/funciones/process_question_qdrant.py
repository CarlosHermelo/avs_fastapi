# app/services/process_question_qdrant.py
import os
import configparser
import logging
import datetime
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_qdrant.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("process_question_qdrant")

def cargar_config_qdrant():
    """Cargar la configuración específica de Qdrant desde el archivo config.ini"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Parámetros de Qdrant
    qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
    collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store')
    
    # Modelo de OpenAI
    modelo = config['DEFAULT'].get('modelo', 'gpt-4o-mini')
    
    return qdrant_url, collection_name, modelo

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
        # Registrar inicio del procesamiento
        start_time = datetime.datetime.now()
        logger.info(f"Procesando pregunta: {question}")
        
        # Cargar configuración
        qdrant_url, collection_name, modelo = cargar_config_qdrant()
        
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
        
        # Ordenar por score (menor score = mayor similitud)
        retrieved_docs.sort(key=lambda x: x[1])
        
        # Extraer documentos y formatear el contexto
        context = "\n\n".join([
            f"fFRAGMENTO: {doc.page_content}\n" +
            f"METADATA: {doc.metadata}\n" +
            f"SCORE: {score}"
            for doc, score in retrieved_docs
        ])
        
        logger.info(f"Se encontraron {len(retrieved_docs)} documentos relevantes.")
        
        # Definir la plantilla para el prompt
        prompt_template = PromptTemplate.from_template(
            """
<CONTEXTO>
La información proporcionada tiene como objetivo apoyar a los agentes que trabajan en las agencias de PAMI, 
quienes se encargan de atender las consultas de los afiliados.
</CONTEXTO>

<ROL>
Eres un asistente virtual experto en los servicios y trámites de PAMI.
</ROL>

<TAREA>
Tu tarea es responder preguntas relacionadas con lo trámites y servicios que ofrece la obra social PAMI,
basándote únicamente en los datos disponibles en la base de datos vectorial. Si la información no está disponible,
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

RESPUESTA:"""
        )
        
        # Preparar el prompt completo con los documentos relevantes
        prompt = prompt_template.format(context=context, question=question)
        
        # Inicializar el modelo LLM
        llm = ChatOpenAI(model=modelo, temperature=0, api_key=openai_api_key)
        
        # Generar respuesta
        logger.info(f"Generando respuesta con modelo {modelo}")
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

if __name__ == "__main__":
    # Ejemplo de uso
    question = "¿Cómo es la afiliación de la esposa de un afiliado?"
    answer = process_question(question)
    print(f"Pregunta: {question}")
    print(f"Respuesta: {answer}") 