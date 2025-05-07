#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para buscar fragmentos en la base de datos vectorial Chroma.
"""

import os
import sys
import configparser
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Configuraciones por defecto
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
        archivo.write(f"CONSULTA CHROMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
    print("\n===== CONSULTA A LA BASE DE DATOS VECTORIAL CHROMA =====\n")
    
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
    
    # Configuración de Chroma
    try:
        # Usar la sección SERVICIOS_SIMAP en lugar de SERVICIOS_SIMAP_Q
        fragment_store_dir = config['SERVICIOS_SIMAP'].get('FRAGMENT_STORE_DIR')
        collection_name = config['SERVICIOS_SIMAP'].get('collection_name_fragmento', DEFAULT_COLLECTION)
        max_results = config['SERVICIOS_SIMAP'].getint('max_results', DEFAULT_RESULTS)
    except Exception as e:
        print(f"Error al leer configuración: {str(e)}")
        print("Usando valores por defecto")
        fragment_store_dir = "./data/SERVICIOS/CHROMA_DB"
        collection_name = DEFAULT_COLLECTION
        max_results = DEFAULT_RESULTS
    
    print(f"Directorio de la base de datos: {fragment_store_dir}")
    print(f"Colección a consultar: {collection_name}")
    print(f"Número máximo de resultados configurado: {max_results}")
    
    # Preguntar si se desea guardar los resultados en un archivo
    guardar_a_archivo = input("¿Desea guardar los resultados en un archivo? (s/n): ").lower() == 's'
    ruta_archivo = None
    
    if guardar_a_archivo:
        ruta_archivo = input("Ingrese la ruta del archivo (o Enter para usar 'resultados_chroma.txt'): ")
        if not ruta_archivo.strip():
            ruta_archivo = "resultados_chroma.txt"
        print(f"Los resultados se guardarán en: {ruta_archivo}")
    
    # Inicializar embeddings de OpenAI
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    
    # Inicializar Chroma con LangChain
    try:
        vector_store = Chroma(
            persist_directory=fragment_store_dir,
            embedding_function=embeddings,
            collection_name=collection_name
        )
        print("Conexión a Chroma establecida")
    except Exception as e:
        print(f"Error al conectar con Chroma: {str(e)}")
        return
    
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
            num_resultados_input = input(f"Número de resultados a mostrar (Enter para usar {max_results} de config.ini): ")
            num_resultados = int(num_resultados_input) if num_resultados_input.strip() else max_results
        except:
            print(f"Valor no válido. Usando {max_results} resultados configurados.")
            num_resultados = max_results
        
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
                        archivo.write(f"CONSULTA CHROMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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