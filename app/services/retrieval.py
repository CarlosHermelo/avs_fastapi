# app/services/retrieval.py
from app.core.config import collection_name_fragmento, fragment_store_directory
from app.core.logging_config import log_message
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import os

embeddings = OpenAIEmbeddings(api_key=os.environ['OPENAI_API_KEY'])
vector_store = Chroma(
    collection_name=collection_name_fragmento,
    persist_directory=fragment_store_directory,
    embedding_function=embeddings
)

def retrieve(query: str, k: int = 4):
    """
    Recupera documentos similares a la consulta del usuario.
    
    Args:
        query: Texto de consulta del usuario
        k: Número de documentos a recuperar (default: 4)
        
    Returns:
        Lista de documentos recuperados
    """
    print(f"[DEBUG-RETRIEVAL] Iniciando recuperación para query: {query}, k={k}")
    log_message(f"Retrieve invocado con query: {query}, k={k}")
    
    try:
        retrieved_docs = vector_store.similarity_search_with_score(query, k=k)
        print(f"[DEBUG-RETRIEVAL] Documentos recuperados con puntuación: {len(retrieved_docs)}")
        
        documentos_relevantes = []
        for doc, score in retrieved_docs:
            print(f"[DEBUG-RETRIEVAL] Documento score: {score:.4f}")
            documentos_relevantes.append(doc)
            
        print(f"[DEBUG-RETRIEVAL] Total documentos relevantes: {len(documentos_relevantes)}")
        return documentos_relevantes
    except Exception as e:
        print(f"[DEBUG-RETRIEVAL] Error en retrieve: {str(e)}")
        # Devolver lista vacía en caso de error
        return []

