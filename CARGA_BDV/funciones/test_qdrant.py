#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la funcionalidad de la base de datos vectorial Qdrant
"""

import configparser
import sys
import json
from carga_bdv_q1 import conectar_a_qdrant, cargar_configuracion
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant

def buscar_en_qdrant_modificado(query, openai_api_key, url_qdrant, collection_name, max_results=5):
    """
    Versión modificada de la función buscar_en_qdrant que corrige los problemas con embeddings.
    """
    # Inicializar cliente y embeddings
    client = QdrantClient(url=url_qdrant)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    try:
        # Verificar que la colección existe
        client.get_collection(collection_name)
    except Exception as e:
        print(f"Error: La colección {collection_name} no existe: {str(e)}")
        return []
    
    # Crear objeto Qdrant para realizar la búsqueda
    qdrant = Qdrant(
        client=client,
        collection_name=collection_name,
        embeddings=embeddings,  # Usar embeddings en lugar de embedding_function
    )
    
    # Realizar la búsqueda
    resultados = qdrant.similarity_search_with_score(
        query=query,
        k=max_results
    )
    
    # Formatear los resultados para devolver
    docs_con_score = []
    for doc, score in resultados:
        docs_con_score.append({
            "contenido": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
    
    print(f"Se encontraron {len(docs_con_score)} resultados para la consulta: '{query}'")
    return docs_con_score

def main():
    # Cargar configuración
    try:
        config = cargar_configuracion()
        
        # Obtener parámetros de configuración
        openai_api_key = config['DEFAULT']['openai_api_key']
        url_qdrant = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
        # Usar directamente fragment_store como nombre de colección
        collection_name = 'fragment_store'
        max_results = int(config['SERVICIOS_SIMAP_Q'].get('max_results', 5))
        
        # Verificar si la colección existe y está accesible
        print(f"Conectando a Qdrant en {url_qdrant}, colección {collection_name}...")
        
        # Inicializar embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        try:
            # Inicializar cliente
            client = QdrantClient(url=url_qdrant)
            
            # Verificar que la colección existe
            client.get_collection(collection_name)
            print(f"Colección {collection_name} encontrada.")
        except Exception as e:
            if "doesn't exist" in str(e):
                # Intentar usar fragment_store como alternativa
                collection_name = 'fragment_store'
                print(f"Intentando conectar a la colección alternativa: {collection_name}")
                try:
                    client = QdrantClient(url=url_qdrant)
                    client.get_collection(collection_name)
                    print(f"Colección alternativa {collection_name} encontrada.")
                except Exception as e2:
                    print(f"Error al conectar con la colección alternativa: {str(e2)}")
                    return 1
            else:
                print(f"Error al conectar con Qdrant: {str(e)}")
                return 1
        
        # Crear objeto Qdrant
        qdrant = Qdrant(
            client=client,
            collection_name=collection_name,
            embeddings=embeddings,  # Usar embeddings en lugar de embedding_function
        )
        
        print("Conexión exitosa a Qdrant.")
        
        # Realizar una búsqueda de prueba
        query = input("\nIngrese consulta para buscar en la base de datos (o 'salir' para terminar): ")
        
        while query.lower() != 'salir':
            try:
                # Realizar búsqueda usando nuestra función modificada
                resultados = buscar_en_qdrant_modificado(
                    query=query,
                    openai_api_key=openai_api_key,
                    url_qdrant=url_qdrant,
                    collection_name=collection_name,
                    max_results=max_results
                )
                
                # Mostrar resultados
                if resultados:
                    print(f"\nResultados para: '{query}'")
                    for i, doc in enumerate(resultados, 1):
                        print(f"\n--- Resultado {i} (Score: {doc['score']:.4f}) ---")
                        print(f"Servicio: {doc['metadata'].get('servicio', 'N/A')}")
                        print(f"Tipo: {doc['metadata'].get('tipo', 'N/A')}")
                        print(f"Subtipo: {doc['metadata'].get('subtipo', 'N/A')}")
                        print(f"ID_SUB: {doc['metadata'].get('id_sub', 'N/A')}")
                        print("\nContenido:")
                        # Mostrar solo primeros 300 caracteres para no saturar la pantalla
                        contenido = doc['contenido']
                        if len(contenido) > 300:
                            contenido = contenido[:300] + "..."
                        print(contenido)
                else:
                    print("No se encontraron resultados.")
            except Exception as e:
                print(f"Error al realizar la búsqueda: {str(e)}")
            
            # Preguntar por nueva consulta
            query = input("\nIngrese nueva consulta (o 'salir' para terminar): ")
        
        print("Prueba completada.")
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 