#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de depuración para identificar problemas con Qdrant
"""

import os
import sys
import traceback

print("Iniciando script de depuración...")

# Verificar versión de Python
print(f"Versión de Python: {sys.version}")

# Intentar importar módulos
try:
    print("Importando configparser...")
    import configparser
    print("configparser importado correctamente")
    
    print("Importando módulos qdrant_client...")
    from qdrant_client import QdrantClient
    print("qdrant_client importado correctamente")
    
    print("Importando módulos de OpenAI...")
    from langchain_openai import OpenAIEmbeddings
    print("langchain_openai importado correctamente")
    
    print("Importando langchain_qdrant...")
    from langchain_qdrant import Qdrant
    print("langchain_qdrant importado correctamente")
except ImportError as e:
    print(f"Error de importación: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Verificar existencia de config.ini
print("\nVerificando archivo config.ini...")
if os.path.exists('config.ini'):
    print("config.ini encontrado")
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Verificar secciones
        print(f"Secciones en config.ini: {config.sections()}")
        
        # Verificar API key
        try:
            openai_api_key = config['DEFAULT'].get('openai_api_key', 'No encontrada')
            if openai_api_key == 'No encontrada':
                print("API key de OpenAI no encontrada en config.ini")
            else:
                print(f"API key de OpenAI encontrada: {openai_api_key[:5]}...")
        except Exception as e:
            print(f"Error al leer API key: {str(e)}")
        
        # Verificar configuración de Qdrant
        try:
            if 'SERVICIOS_SIMAP_Q' in config:
                print("\nInformación de SERVICIOS_SIMAP_Q:")
                qdrant_url = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'No encontrada')
                collection_name = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'No encontrada')
                
                print(f"  - URL de Qdrant: {qdrant_url}")
                print(f"  - Nombre de colección: {collection_name}")
            else:
                print("Sección SERVICIOS_SIMAP_Q no encontrada en config.ini")
        except Exception as e:
            print(f"Error al leer configuración de Qdrant: {str(e)}")
            
    except Exception as e:
        print(f"Error al procesar config.ini: {str(e)}")
        traceback.print_exc()
else:
    print("ADVERTENCIA: Archivo config.ini no encontrado")

# Intentar conectar a Qdrant
print("\nIntentando conectar a Qdrant...")
try:
    url_qdrant = "http://localhost:6333"
    print(f"URL de Qdrant: {url_qdrant}")
    
    client = QdrantClient(url=url_qdrant)
    print("Conexión con Qdrant establecida exitosamente")
    
    # Intentar listar colecciones
    print("\nListando colecciones de Qdrant...")
    try:
        colecciones = client.get_collections()
        print(f"Respuesta de get_collections(): {colecciones}")
        
        if hasattr(colecciones, 'collections'):
            collection_names = [c.name for c in colecciones.collections]
            print(f"Colecciones encontradas: {collection_names}")
        else:
            print("La respuesta de get_collections() no tiene el atributo 'collections'")
            print(f"Tipo de respuesta: {type(colecciones)}")
    except Exception as e:
        print(f"Error al listar colecciones: {str(e)}")
        traceback.print_exc()
except Exception as e:
    print(f"Error al conectar con Qdrant: {str(e)}")
    traceback.print_exc()

print("\nFin del script de depuración.") 