# Importación de las librerías necesarias
import datetime
import json
import configparser
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
import html
import re

# Cargar la configuración desde config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Obtener las variables de configuración
try:
    nombre_archivo_json = config['SERVICIOS_SIMAP']['nombre_archivo_json']
    directorio_archivo_json = config['SERVICIOS_SIMAP']['directorio_archivo_json']
    ruta_archivo_json = f"{directorio_archivo_json}/{nombre_archivo_json}"
    openai_api_key = config['DEFAULT']['openai_api_key']
    directorio_bdvectorial = config['SERVICIOS_SIMAP']['FRAGMENT_STORE_DIR']
    nombre_bdvectorial = config['SERVICIOS_SIMAP']['nombre_bdvectorial']
except KeyError as e:
    raise ValueError(f"Falta la clave de configuración: {e}")

# Función para normalizar texto
def normalizar_texto(texto):
    if texto is None:
        return ""
    
    # 1. Decodificar entidades HTML
    texto_decodificado = html.unescape(texto)
    
    # 2. Reemplazar saltos de línea y espacios redundantes
    texto_decodificado = texto_decodificado.replace("\r", " ").replace("\n", " ")
    
    # 3. Reemplazar múltiples espacios por uno solo
    texto_limpio = re.sub(r'\s+', ' ', texto_decodificado)
    
    # 4. Eliminar espacios al inicio y al final
    return texto_limpio.strip()

# Función principal para cargar JSON en la base de datos vectorial
def cargar_json_a_chroma(ruta_archivo_json, openai_api_key, directorio_bdvectorial, nombre_bdvectorial):
    with open(ruta_archivo_json, 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)

    documentos = []
    registros = data.get("RECORDS", [])
    
    # Procesar cada registro como un chunk individual
    for item in registros:
        servicio = normalizar_texto(item.get("SERVICIO", ""))
        tipo = normalizar_texto(item.get("TIPO", ""))
        subtipo = normalizar_texto(item.get("SUBTIPO", ""))
        id_sub = item.get("ID_SUB", "")

        # Concatenar los campos de interés en un solo texto
        texto_chunk = "\n".join([
            f"COPETE: {normalizar_texto(item.get('COPETE', ''))}",
            f"CONSISTE: {normalizar_texto(item.get('CONSISTE', ''))}",
            f"REQUISITOS: {normalizar_texto(item.get('REQUISITOS', ''))}",
            f"PAUTAS: {normalizar_texto(item.get('PAUTAS', ''))}",
            f"QUIEN_PUEDE: {normalizar_texto(item.get('QUIEN_PUEDE', ''))}",
            f"QUIENES_PUEDEN: {normalizar_texto(item.get('QUIENES_PUEDEN', ''))}",
            f"COMO_LO_HACEN: {normalizar_texto(item.get('COMO_LO_HACEN', ''))}"
        ])

        # Crear el documento con metadata
        documento = Document(
            page_content=texto_chunk,
            metadata={
                "servicio": servicio,
                "tipo": tipo,
                "subtipo": subtipo,
                "id_sub": id_sub
            }
        )
        documentos.append(documento)

    # Cargar los documentos en la base de datos vectorial
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vector_db = Chroma.from_documents(
        documents=documentos,
        embedding=embeddings,
        persist_directory=directorio_bdvectorial,
        collection_name=nombre_bdvectorial
    )
    print(f"Se han cargado {len(documentos)} documentos en la base de datos vectorial.")

# Llamada de ejemplo a la función
cargar_json_a_chroma(ruta_archivo_json, openai_api_key, directorio_bdvectorial, nombre_bdvectorial)
