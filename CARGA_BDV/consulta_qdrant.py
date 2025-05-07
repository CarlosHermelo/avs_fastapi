#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para buscar fragmentos en la base de datos vectorial Qdrant.
"""

import os
import sys
import configparser
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant

# Configuraciones por defecto
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "fragment_store"
DEFAULT_RESULTS = 5

def buscar_config_ini():
    """Busca el archivo config.ini en diferentes ubicaciones."""
    # Lista de posibles ubicaciones del archivo config.ini
    posibles_rutas = [
        'config.ini',                           # En el directorio actual
        '../config.ini',                        # En el directorio padre
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),  # En la carpeta del script
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')  # En la carpeta padre del script
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            print(f"Archivo config.ini encontrado en: {ruta}")
            return ruta
    
    print("ADVERTENCIA: No se encontró el archivo config.ini")
    return None

def guardar_resultados(resultados, pregunta, ruta_archivo):
    """Guarda los resultados de la búsqueda en un archivo."""
    with open(ruta_archivo, 'a', encoding='utf-8') as archivo:
        archivo.write(f"\n{'='*50}\n")
        archivo.write(f"CONSULTA QDRANT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        archivo.write(f"Pregunta: {pregunta}\n")
        archivo.write(f"Resultados encontrados: {len(resultados)}\n")
        archivo.write(f"{'='*50}\n\n")
        
        for i, (doc, score) in enumerate(resultados, 1):
            archivo.write(f"\n----- Fragmento #{i} (Score: {score:.4f}) -----\n")
            archivo.write(f"Contenido:\n{doc.page_content}\n")
            
            if doc.metadata:
                archivo.write("\nMetadatos:\n")
                for key, value in doc.metadata.items():
                    archivo.write(f"  - {key}: {value}\n")
            
            archivo.write("-" * 70 + "\n")
        
        archivo.write("\n\n")
    
    print(f"Resultados guardados en {ruta_archivo}")

def main():
    print("\n===== CONSULTA A LA BASE DE DATOS VECTORIAL QDRANT =====\n")
    
    # Buscar y cargar configuración
    ruta_config = buscar_config_ini()
    if not ruta_config:
        print("Error: No se pudo encontrar el archivo config.ini")
        return
    
    config = configparser.ConfigParser()
    config.read(ruta_config)
    
    # Obtener API key de OpenAI
    openai_api_key = config['DEFAULT'].get('openai_api_key')
    if not openai_api_key:
        print("Error: No se encontró la API key de OpenAI en config.ini")
        return
    
    print(f"API key de OpenAI encontrada: {openai_api_key[:5]}...")
    
    # Configuración de Qdrant
    try:
        qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', DEFAULT_QDRANT_URL)
        collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', DEFAULT_COLLECTION)
    except:
        qdrant_url = DEFAULT_QDRANT_URL
        collection_name = DEFAULT_COLLECTION
    
    print(f"URL de Qdrant: {qdrant_url}")
    print(f"Colección a consultar: {collection_name}")
    
    # Preguntar si se desea guardar los resultados en un archivo
    guardar_a_archivo = input("¿Desea guardar los resultados en un archivo? (s/n): ").lower() == 's'
    ruta_archivo = None
    
    if guardar_a_archivo:
        ruta_archivo = input("Ingrese la ruta del archivo (o Enter para usar 'resultados_qdrant.txt'): ")
        if not ruta_archivo.strip():
            ruta_archivo = "resultados_qdrant.txt"
        print(f"Los resultados se guardarán en: {ruta_archivo}")
    
    # Conectar a Qdrant
    try:
        client = QdrantClient(url=qdrant_url)
        print("Conexión a Qdrant establecida")
        
        # Verificar colecciones disponibles
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        print(f"Colecciones disponibles: {collection_names}")
        
        if collection_name not in collection_names:
            print(f"Error: La colección '{collection_name}' no existe.")
            
            # Preguntar si quiere usar otra colección disponible
            if collection_names:
                use_alternative = input(f"¿Desea usar la colección '{collection_names[0]}' en su lugar? (s/n): ")
                if use_alternative.lower() == 's':
                    collection_name = collection_names[0]
                    print(f"Usando colección alternativa: {collection_name}")
                else:
                    return
            else:
                print("No hay colecciones disponibles.")
                return
    except Exception as e:
        print(f"Error al conectar con Qdrant: {str(e)}")
        return
    
    # Inicializar embeddings de OpenAI
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    
    # Inicializar Qdrant con LangChain
    vector_store = Qdrant(
        client=client,
        collection_name=collection_name,
        embeddings=embeddings
    )
    
    print("\nTodo listo para realizar consultas.")
    
    # Bucle de consulta
    while True:
        # Solicitar pregunta al usuario
        print("\n" + "-"*50)
        pregunta = input("\nIngrese su pregunta (o 'salir' para terminar): ")
        
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            print("Finalizando programa...")
            break
        
        if not pregunta.strip():
            print("Pregunta vacía. Intente de nuevo.")
            continue
        
        # Solicitar número de resultados
        try:
            num_resultados_input = input(f"Número de resultados a mostrar (Enter para usar {DEFAULT_RESULTS}): ")
            num_resultados = int(num_resultados_input) if num_resultados_input.strip() else DEFAULT_RESULTS
        except:
            print(f"Valor no válido. Usando {DEFAULT_RESULTS} resultados.")
            num_resultados = DEFAULT_RESULTS
        
        # Realizar búsqueda
        print(f"\nBuscando: '{pregunta}'")
        print(f"Recuperando hasta {num_resultados} resultados...\n")
        
        try:
            resultados = vector_store.similarity_search_with_score(
                query=pregunta,
                k=num_resultados
            )
            
            # Mostrar resultados
            if resultados:
                print(f"\n===== Se encontraron {len(resultados)} fragmentos relevantes =====\n")
                
                for i, (doc, score) in enumerate(resultados, 1):
                    print(f"\n----- Fragmento #{i} (Score: {score:.4f}) -----")
                    print(f"Contenido:\n{doc.page_content}")
                    
                    if doc.metadata:
                        print("\nMetadatos:")
                        for key, value in doc.metadata.items():
                            print(f"  - {key}: {value}")
                    
                    print("-" * 70)
                
                # Guardar resultados si se solicitó
                if guardar_a_archivo and ruta_archivo:
                    guardar_resultados(resultados, pregunta, ruta_archivo)
            else:
                print("No se encontraron fragmentos relevantes para esta pregunta.")
                if guardar_a_archivo and ruta_archivo:
                    with open(ruta_archivo, 'a', encoding='utf-8') as archivo:
                        archivo.write(f"\n{'='*50}\n")
                        archivo.write(f"CONSULTA QDRANT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        archivo.write(f"Pregunta: {pregunta}\n")
                        archivo.write("No se encontraron fragmentos relevantes para esta pregunta.\n")
                        archivo.write(f"{'='*50}\n\n")
                
        except Exception as e:
            print(f"Error al realizar la búsqueda: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n===== PROGRAMA FINALIZADO =====") 