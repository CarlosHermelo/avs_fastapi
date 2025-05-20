#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para buscar fragmentos en la base de datos vectorial Qdrant.
"""

import os
import sys
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import Qdrant # LangChainDeprecationWarning: Qdrant -> QdrantVectorStore
from dotenv import load_dotenv

# --- Carga de Configuración a Nivel de Módulo ---
_DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

if os.path.exists(_DOTENV_PATH):
    # Cargar .env, pero no sobrescribir variables de entorno existentes
    load_dotenv(dotenv_path=_DOTENV_PATH, override=False)
    print(f"Cargando configuracion desde: {_DOTENV_PATH}")
    # Si OPENAI_API_KEY ya existe en el entorno, python-dotenv (con override=False) no la cambiará.
    # Si no existe, tomará el valor del .env.
else:
    # Si .env no está en la ruta esperada, intenta cargar (puede que encuentre uno en CWD o nada)
    load_dotenv(override=False)
    print(f"Archivo .env no encontrado en {_DOTENV_PATH}, intentando carga estándar.")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
COLLECTION_NAME = os.getenv('COLLECTION_NAME_FRAGMENTO', 'fragment_store')
DEFAULT_RESULTS = int(os.getenv('MAX_RESULTS', '5'))

if not OPENAI_API_KEY:
    print("CRÍTICO: La variable de entorno OPENAI_API_KEY no está configurada.")
    print("Por favor, asegúrate de que esté definida en tu archivo .env o en tu entorno.")
    # sys.exit(1) # Podrías salir aquí si es crítico
elif OPENAI_API_KEY.startswith("sk-proj-"):
    print("ADVERTENCIA: La OPENAI_API_KEY configurada comienza con 'sk-proj-'.")
    print("Este tipo de clave es para Proyectos de OpenAI y usualmente no funciona para llamadas directas a la API de embeddings.")
    print("Por favor, asegúrate de usar una Clave Secreta (Secret Key) que comience con 'sk-'.")
    print("Puedes obtener una nueva Clave Secreta en: https://platform.openai.com/account/api-keys")

# --- Fin de Carga de Configuración ---

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
    
    if not OPENAI_API_KEY:
        # Esta verificación ya se hace arriba, pero es bueno tenerla antes de usar la clave.
        print("Error: OPENAI_API_KEY no está disponible. Revisa la configuración.")
        return
    
    print(f"API key de OpenAI (parcialmente oculta): {OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 9 else ''}")
    print(f"URL de Qdrant: {QDRANT_URL}")
    print(f"Colección a consultar: {COLLECTION_NAME}")
    
    guardar_a_archivo = input("¿Desea guardar los resultados en un archivo? (s/n): ").lower() == 's'
    ruta_archivo = None
    
    if guardar_a_archivo:
        ruta_archivo_input = input("Ingrese la ruta del archivo (o Enter para usar 'resultados_qdrant.txt'): ")
        ruta_archivo = ruta_archivo_input.strip() if ruta_archivo_input.strip() else "resultados_qdrant.txt"
        print(f"Los resultados se guardarán en: {ruta_archivo}")
    
    current_collection_name = COLLECTION_NAME # Para permitir cambio si la colección no existe
    try:
        client = QdrantClient(url=QDRANT_URL)
        print("Conexión a Qdrant establecida.")
        
        collections_response = client.get_collections()
        available_collections = [c.name for c in collections_response.collections]
        print(f"Colecciones disponibles: {available_collections}")
        
        if current_collection_name not in available_collections:
            print(f"Error: La colección '{current_collection_name}' no existe.")
            if available_collections:
                use_alternative = input(f"¿Desea usar la colección '{available_collections[0]}' en su lugar? (s/n): ").lower()
                if use_alternative == 's':
                    current_collection_name = available_collections[0]
                    print(f"Usando colección alternativa: {current_collection_name}")
                else:
                    print("Operación cancelada por el usuario.")
                    return
            else:
                print("No hay colecciones disponibles en Qdrant.")
                return
    except Exception as e:
        print(f"Error al conectar con Qdrant o verificar colección: {str(e)}")
        return
    
    try:
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY) # Aquí se usa la OPENAI_API_KEY
    except Exception as e:
        print(f"Error al inicializar OpenAIEmbeddings: {str(e)}")
        print("Verifica que la OPENAI_API_KEY sea correcta (debe ser una Clave Secreta sk-...) y que tengas conexión a internet.")
        return

    try:
        vector_store = Qdrant( # Esta clase está deprecada
            client=client,
            collection_name=current_collection_name,
            embeddings=embeddings
        )
    except Exception as e:
        print(f"Error al inicializar Qdrant (vector_store): {str(e)}")
        return
    
    print("\nTodo listo para realizar consultas.")
    
    while True:
        print("\n" + "-"*50)
        pregunta = input("\nIngrese su pregunta (o 'salir' para terminar): ")
        
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            print("Finalizando programa...")
            break
        
        if not pregunta.strip():
            print("Pregunta vacía. Intente de nuevo.")
            continue
        
        try:
            num_resultados_input = input(f"Número de resultados a mostrar (Enter para usar {DEFAULT_RESULTS}): ")
            num_resultados = int(num_resultados_input) if num_resultados_input.strip() else DEFAULT_RESULTS
            if num_resultados <= 0:
                print("El número de resultados debe ser positivo. Usando valor por defecto.")
                num_resultados = DEFAULT_RESULTS
        except ValueError:
            print(f"Valor no válido para número de resultados. Usando {DEFAULT_RESULTS} resultados.")
            num_resultados = DEFAULT_RESULTS
        
        print(f"\nBuscando: '{pregunta}'")
        print(f"Recuperando hasta {num_resultados} resultados...\n")
        
        try:
            resultados = vector_store.similarity_search_with_score(
                query=pregunta,
                k=num_resultados
            )
            
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
            print("Detalles del error:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
    except Exception as e:
        print(f"\nError inesperado en la ejecución: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n===== PROGRAMA FINALIZADO =====") 