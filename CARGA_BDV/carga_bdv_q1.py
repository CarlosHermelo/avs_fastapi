# Importación de las librerías necesarias
import datetime
import json
import configparser
import os
import sys
import argparse
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import Qdrant
from langchain.schema import Document
import html
import re
import time

# Función para encontrar y cargar el archivo config.ini
def cargar_configuracion():
    # Posibles ubicaciones del archivo config.ini
    posibles_rutas = [
        'config.ini',                   # En el directorio actual
        '../config.ini',                # En el directorio padre
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),  # En el mismo directorio que este script
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')  # En el directorio padre del script
    ]
    
    # Buscar el archivo en las posibles ubicaciones
    config_path = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            config_path = ruta
            break
    
    if not config_path:
        raise FileNotFoundError("No se pudo encontrar el archivo config.ini. Asegúrate de que el archivo exista en el directorio actual o en el directorio padre.")
    
    print(f"Usando archivo de configuración: {config_path}")
    
    # Cargar la configuración
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

# Parsear argumentos de línea de comandos
def parsear_argumentos():
    parser = argparse.ArgumentParser(description='Cargar datos de JSON a base de datos vectorial Qdrant')
    parser.add_argument('--limite', type=int, default=0, help='Limitar el número de registros a cargar (0 = sin límite)')
    parser.add_argument('--modo-prueba', action='store_true', help='Ejecutar en modo prueba (carga solo 10 registros)')
    parser.add_argument('--qdrant-path', type=str, help='Ruta alternativa para el almacenamiento de Qdrant (ej: D:/qdrant)')
    parser.add_argument('--comprobar-espacio', action='store_true', help='Verificar espacio disponible antes de iniciar la carga')
    parser.add_argument('--no-borrar', action='store_true', help='No borrar la colección existente (añadir a la existente)')
    return parser.parse_args()

# Cargar la configuración desde config.ini
try:
    config = cargar_configuracion()
    args = parsear_argumentos()
    
    # Parámetros principales
    nombre_archivo_json = config['SERVICIOS_SIMAP_Q']['nombre_archivo_json']
    directorio_archivo_json = config['SERVICIOS_SIMAP_Q']['directorio_archivo_json']
    ruta_archivo_json = f"{directorio_archivo_json}/{nombre_archivo_json}"
    openai_api_key = config['DEFAULT']['openai_api_key']
    
    # Usar URL alternativa si se especificó en línea de comandos
    if args.qdrant_path:
        url_qdrant = f"http://localhost:6333?path={args.qdrant_path}"
        print(f"Usando ruta alternativa para Qdrant: {args.qdrant_path}")
    else:
        url_qdrant = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
    
    # Resto de parámetros
    nombre_bdvectorial = config['SERVICIOS_SIMAP_Q']['nombre_bdvectorial']
    
    # Parámetros adicionales
    tamano_chunk = int(config['SERVICIOS_SIMAP_Q'].get('tamano_chunk', 300))
    overlap_chunk = int(config['SERVICIOS_SIMAP_Q'].get('overlap_chunk', 50))
    max_context_tokens = int(config['SERVICIOS_SIMAP_Q'].get('max_context_tokens', 80))
    collection_name_fragmento = config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store')
    
    # Fechas (si son relevantes)
    fecha_desde = config['SERVICIOS_SIMAP_Q'].get('fecha_desde', '2024-01-01')
    fecha_hasta = config['SERVICIOS_SIMAP_Q'].get('fecha_hasta', '2024-12-31')
    max_results = int(config['SERVICIOS_SIMAP_Q'].get('max_results', 20))
    
    # Verificar espacio disponible
    if args.comprobar_espacio:
        import shutil
        from pathlib import Path
        
        # Extraer unidad del URL si tiene formato path
        if "?path=" in url_qdrant:
            path_part = url_qdrant.split("?path=")[1]
            drive = os.path.splitdrive(path_part)[0]
            if drive:
                # Si tiene unidad especificada
                target_path = drive + "\\"
            else:
                # Si es una ruta relativa, usar directorio actual
                target_path = os.getcwd()
        else:
            # Si no hay path, usar directorio actual
            target_path = os.getcwd()
        
        # Verificar espacio disponible
        total, used, free = shutil.disk_usage(target_path)
        print(f"\nVerificación de espacio en disco:")
        print(f"Ubicación: {target_path}")
        print(f"Total: {total // (1024**3)} GB")
        print(f"Usado: {used // (1024**3)} GB")
        print(f"Libre: {free // (1024**3)} GB")
        
        # Espacio mínimo recomendado: 1GB por cada 1000 registros
        estimado_por_registro = 1 * 1024**3 / 1000  # 1GB/1000 registros
        espacio_recomendado = estimado_por_registro * (limite_registros if limite_registros > 0 else 1000)
        
        if free < espacio_recomendado:
            print(f"\n⚠️ ADVERTENCIA: Posible espacio insuficiente")
            print(f"Se recomienda al menos {espacio_recomendado // (1024**3)} GB libres")
            
            respuesta = input("\n¿Desea continuar de todos modos? (s/n): ")
            if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Operación cancelada por el usuario.")
                sys.exit(0)
    
except FileNotFoundError as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
except KeyError as e:
    print(f"Error: Falta la clave de configuración: {e}")
    sys.exit(1)

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

# Función para borrar una colección en Qdrant
def borrar_coleccion(client, collection_name):
    """Borra una colección en Qdrant si existe"""
    try:
        # Verificar si la colección existe
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if collection_name in collection_names:
            print(f"Borrando colección existente: {collection_name}")
            client.delete_collection(collection_name=collection_name)
            print(f"Colección {collection_name} borrada exitosamente")
            return True
        else:
            print(f"La colección {collection_name} no existe. No es necesario borrarla.")
            return False
    except Exception as e:
        print(f"Error al borrar la colección {collection_name}: {str(e)}")
        return False

# Función para crear una colección vacía en Qdrant
def crear_coleccion_vacia(client, collection_name, vector_size=1536):
    """Crea una colección vacía en Qdrant"""
    try:
        print(f"Creando nueva colección: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,  # Para OpenAI embeddings
                distance=models.Distance.COSINE
            )
        )
        print(f"Colección {collection_name} creada exitosamente")
        return True
    except Exception as e:
        print(f"Error al crear la colección {collection_name}: {str(e)}")
        return False

# Función para obtener estadísticas de la colección
def obtener_estadisticas_coleccion(client, collection_name):
    """Obtiene estadísticas de la colección en Qdrant"""
    try:
        return client.get_collection(collection_name=collection_name)
    except Exception as e:
        print(f"Error al obtener estadísticas de la colección {collection_name}: {str(e)}")
        return None

# Función principal para cargar JSON en la base de datos vectorial Qdrant
def cargar_json_a_qdrant(ruta_archivo_json, openai_api_key, url_qdrant, nombre_bdvectorial, collection_name=None, limite_registros=0, borrar_existente=True):
    collection_name = collection_name or nombre_bdvectorial
    
    print(f"\n{'='*80}")
    print(f"CARGA DE DATOS A QDRANT")
    print(f"{'='*80}")
    print(f"Fecha y hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Archivo de origen: {ruta_archivo_json}")
    print(f"URL de Qdrant: {url_qdrant}")
    print(f"Colección destino: {collection_name}")
    
    # Inicializar el cliente Qdrant
    client = QdrantClient(url=url_qdrant)
    
    # Métricas de carga iniciales
    metricas = {
        "documentos_procesados": 0,
        "documentos_cargados": 0,
        "tiempo_inicio": time.time(),
        "tiempo_fin": None,
        "coleccion_anterior_borrada": False,
        "coleccion_creada": False
    }
    
    # 1. Borrar la colección existente si se indica
    if borrar_existente:
        metricas["coleccion_anterior_borrada"] = borrar_coleccion(client, collection_name)
    else:
        print(f"Manteniendo colección existente: {collection_name}")
    
    # 2. Crear una nueva colección vacía
    if borrar_existente or not collection_exists(client, collection_name):
        metricas["coleccion_creada"] = crear_coleccion_vacia(client, collection_name)
    
    # Verificar si el archivo existe
    if not os.path.exists(ruta_archivo_json):
        print(f"Error: El archivo {ruta_archivo_json} no existe.")
        # Intentar buscar el archivo en el directorio actual o directorio padre
        posibles_rutas = [
            os.path.basename(ruta_archivo_json),
            os.path.join('..', os.path.basename(ruta_archivo_json)),
            os.path.join('data', 'json', os.path.basename(ruta_archivo_json)),
            os.path.join('..', 'data', 'json', os.path.basename(ruta_archivo_json))
        ]
        
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                ruta_archivo_json = ruta
                print(f"Se encontró el archivo en: {ruta_archivo_json}")
                break
        else:
            print("No se pudo encontrar el archivo JSON. Por favor, verifica la ruta en config.ini.")
            return None, metricas
    
    # Cargar el archivo JSON
    print(f"\nCargando datos desde: {ruta_archivo_json}")
    with open(ruta_archivo_json, 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)

    documentos = []
    registros = data.get("RECORDS", [])
    
    total_registros = len(registros)
    print(f"Total de registros encontrados en el JSON: {total_registros}")
    
    # Si se especifica un límite de registros, recortar la lista
    if limite_registros > 0 and limite_registros < total_registros:
        print(f"MODO PRUEBA: Limitando a {limite_registros} registros")
        registros = registros[:limite_registros]
    
    # Contador para seguimiento del progreso
    contador = 0
    total = len(registros)
    
    # Inicio de procesamiento de registros
    print(f"\nIniciando procesamiento de {total} registros...")
    start_time_process = time.time()
    
    # Procesar cada registro como un chunk individual
    for item in registros:
        # Actualizar y mostrar progreso
        contador += 1
        if contador % 10 == 0 or contador == 1 or contador == total:
            tiempo_transcurrido = time.time() - start_time_process
            velocidad = contador / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
            tiempo_estimado = (total - contador) / velocidad if velocidad > 0 else 0
            print(f"Procesando registro {contador}/{total} ({contador/total*100:.1f}%) - {velocidad:.1f} reg/s - Tiempo restante est.: {tiempo_estimado/60:.1f} min")
        
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
                "id_sub": id_sub,
                "fecha_carga": datetime.datetime.now().isoformat()
            }
        )
        documentos.append(documento)
        metricas["documentos_procesados"] += 1

    print(f"Procesados {len(documentos)} documentos para vectorización")
    
    # Inicializar el objeto de embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    # 3. Cargar los documentos en la colección
    print(f"\nCargando {len(documentos)} documentos en Qdrant...")
    start_time_upload = time.time()
    
    try:
        # Crear o conectar a la colección de Qdrant usando LangChain
        vector_db = Qdrant.from_documents(
            documents=documentos,
            embedding=embeddings,
            url=url_qdrant,
            collection_name=collection_name,
            prefer_grpc=False,  # Usar HTTP en lugar de gRPC
        )
        
        metricas["documentos_cargados"] = len(documentos)
        metricas["tiempo_fin"] = time.time()
        
        # Obtener estadísticas finales de la colección
        try:
            stats = obtener_estadisticas_coleccion(client, collection_name)
        except Exception as e:
            print(f"Advertencia: No se pudieron obtener estadísticas de la colección: {str(e)}")
            stats = None
        
        # Mostrar resumen de carga
        tiempo_total = metricas["tiempo_fin"] - metricas["tiempo_inicio"]
        tiempo_proceso = start_time_upload - start_time_process
        tiempo_carga = metricas["tiempo_fin"] - start_time_upload
        
        print(f"\n{'='*80}")
        print(f"RESUMEN DE CARGA COMPLETADA")
        print(f"{'='*80}")
        print(f"Fecha y hora fin: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Registros procesados: {metricas['documentos_procesados']}")
        print(f"Documentos cargados: {metricas['documentos_cargados']}")
        print(f"Colección borrada previamente: {'Sí' if metricas['coleccion_anterior_borrada'] else 'No'}")
        print(f"Nueva colección creada: {'Sí' if metricas['coleccion_creada'] else 'No'}")
        print(f"Tiempo total: {tiempo_total:.2f} segundos ({tiempo_total/60:.2f} minutos)")
        print(f"  - Tiempo de procesamiento: {tiempo_proceso:.2f} segundos")
        print(f"  - Tiempo de carga en Qdrant: {tiempo_carga:.2f} segundos")
        
        if stats:
            print(f"\nEstadísticas de la colección {collection_name}:")
            print(f"  - Vectores: {stats.vectors_count}")
            try:
                vector_size = stats.config.params.size
                distance = stats.config.params.distance
                print(f"  - Dimensión de vectores: {vector_size}")
                print(f"  - Métrica de distancia: {distance}")
            except AttributeError:
                # Manejar diferencias en la estructura de la respuesta según la versión de Qdrant
                try:
                    print(f"  - Dimensión de vectores: {getattr(stats.config.vector_params, 'size', 'Desconocido')}")
                    print(f"  - Métrica de distancia: {getattr(stats.config.vector_params, 'distance', 'Desconocido')}")
                except Exception as e:
                    print(f"  - No se pudieron obtener detalles de la colección: {str(e)}")
        
        print(f"{'='*80}")
        
        return vector_db, metricas
        
    except Exception as e:
        print(f"Error durante la carga a Qdrant: {str(e)}")
        metricas["tiempo_fin"] = time.time()
        metricas["error"] = str(e)
        return None, metricas

# Función para verificar si una colección existe
def collection_exists(client, collection_name):
    """Verifica si una colección existe en Qdrant"""
    try:
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        return collection_name in collection_names
    except Exception:
        return False

# Función para buscar en la base de datos vectorial
def buscar_en_qdrant(query, openai_api_key, url_qdrant, collection_name, max_results=5):
    """
    Realiza una búsqueda semántica en la base de datos vectorial Qdrant.
    
    Args:
        query (str): La consulta de búsqueda.
        openai_api_key (str): La clave API de OpenAI.
        url_qdrant (str): URL del servidor Qdrant.
        collection_name (str): Nombre de la colección a consultar.
        max_results (int): Número máximo de resultados a retornar.
        
    Returns:
        list: Lista de documentos similares con sus metadatos.
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
        embedding_function=embeddings.embed_query,
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

# Función para conectar a una colección existente
def conectar_a_qdrant(openai_api_key, url_qdrant, collection_name):
    """
    Conecta a una colección existente de Qdrant.
    
    Args:
        openai_api_key (str): La clave API de OpenAI.
        url_qdrant (str): URL del servidor Qdrant.
        collection_name (str): Nombre de la colección a conectar.
        
    Returns:
        Qdrant: Objeto Qdrant para interactuar con la colección.
    """
    # Inicializar cliente y embeddings
    client = QdrantClient(url=url_qdrant)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    try:
        # Verificar que la colección existe
        client.get_collection(collection_name)
        print(f"Conectado a la colección {collection_name} en Qdrant")
    except Exception as e:
        print(f"Error: La colección {collection_name} no existe: {str(e)}")
        raise ValueError(f"La colección {collection_name} no existe")
    
    # Crear y devolver objeto Qdrant
    qdrant = Qdrant(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings.embed_query,
    )
    
    return qdrant

# Función para verificar la carga exitosa
def verificar_carga_exitosa(client, collection_name, expected_count):
    """Verifica que la colección existe y contiene el número esperado de documentos"""
    try:
        # Verificar que la colección existe
        info = client.get_collection(collection_name)
        
        if info.vectors_count is None:
            # Si no podemos obtener el conteo, verificamos de otra manera que la colección exista
            colecciones = client.get_collections().collections
            existe = any(col.name == collection_name for col in colecciones)
            if existe:
                print(f"La colección {collection_name} existe, pero no se pudo verificar el conteo de vectores.")
                return True
            else:
                print(f"La colección {collection_name} no existe.")
                return False
        
        # Si tenemos conteo, verificar que coincida aproximadamente
        actual_count = info.vectors_count
        
        # Permitimos una pequeña diferencia por si acaso
        if actual_count >= expected_count * 0.9:  # Al menos 90% de los documentos esperados
            print(f"Verificación exitosa: La colección contiene {actual_count} vectores.")
            return True
        else:
            print(f"Advertencia: Se esperaban aproximadamente {expected_count} vectores, pero la colección contiene {actual_count}.")
            return False
            
    except Exception as e:
        print(f"Error al verificar la carga: {str(e)}")
        return False

if __name__ == "__main__":
    print("Iniciando carga de datos a Qdrant...")
    
    # Determinar el límite de registros
    limite_registros = 0
    if args.modo_prueba:
        limite_registros = 10
        print("Ejecutando en modo prueba: se cargarán solo 10 registros")
    elif args.limite > 0:
        limite_registros = args.limite
        print(f"Limitando la carga a {limite_registros} registros")
    
    # Determinar si se debe borrar la colección existente
    borrar_existente = not args.no_borrar
    if args.no_borrar:
        print("Modo NO-BORRAR: Se añadirán documentos a la colección existente")
    else:
        print("Modo RECREAR: Se borrará la colección existente antes de cargar los nuevos documentos")
    
    # Llamada a la función con los parámetros de configuración
    vector_db, metricas = cargar_json_a_qdrant(
        ruta_archivo_json=ruta_archivo_json, 
        openai_api_key=openai_api_key, 
        url_qdrant=url_qdrant, 
        nombre_bdvectorial=nombre_bdvectorial,
        collection_name=collection_name_fragmento,
        limite_registros=limite_registros,
        borrar_existente=borrar_existente
    )
    
    # Verificar que la carga fue exitosa
    cliente = QdrantClient(url=url_qdrant)
    verificacion_exitosa = False
    
    if vector_db is not None:
        # Verificar que la colección existe y tiene el número esperado de documentos
        verificacion_exitosa = verificar_carga_exitosa(
            cliente, 
            collection_name_fragmento, 
            metricas["documentos_procesados"]
        )
    
    if verificacion_exitosa:
        print("Proceso completado correctamente.")
        # Guardar métricas en un archivo para análisis posterior
        try:
            with open(f"metricas_carga_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                json.dump({
                    "fecha": datetime.datetime.now().isoformat(),
                    "documentos_procesados": metricas["documentos_procesados"],
                    "documentos_cargados": metricas["documentos_cargados"],
                    "tiempo_total_segundos": metricas["tiempo_fin"] - metricas["tiempo_inicio"],
                    "coleccion_borrada": metricas["coleccion_anterior_borrada"],
                    "coleccion_creada": metricas["coleccion_creada"]
                }, f)
                print(f"Métricas guardadas en archivo.")
        except Exception as e:
            print(f"Advertencia: No se pudieron guardar las métricas: {str(e)}")
    else:
        print("Error: No se pudo completar el proceso de carga. Revisa los mensajes anteriores.") 