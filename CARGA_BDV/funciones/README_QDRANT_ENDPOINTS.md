# Adaptación de los Endpoints a Qdrant

Este proyecto adapta los endpoints originales que usaban Chroma DB para utilizar Qdrant como base de datos vectorial. La estructura de directorios y componentes principales se ha mantenido, modificando solo las partes necesarias para la integración con Qdrant.

## Archivos Adaptados

- **endpoint1_qdrant.py**: Versión del endpoint FastAPI adaptada para usar Qdrant en lugar de Chroma.
- **process_question_qdrant.py**: Servicio para procesar preguntas utilizando Qdrant.
- **config_qdrant.py**: Utilidades para cargar la configuración específica de Qdrant.
- **client_test_qdrant.py**: Cliente de prueba para los endpoints con Qdrant.

## Configuración

La configuración de Qdrant se especifica en el archivo `config.ini` en la sección `[SERVICIOS_SIMAP_Q]`:

```ini
[SERVICIOS_SIMAP_Q]
# Configuración para la base de datos vectorial Qdrant
fecha_desde = 2024-02-08
fecha_hasta = 2024-12-10
max_results = 20

nombre_bdvectorial = fragment_store
qdrant_url = http://localhost:6333

# Para especificar una ubicación específica para los datos de Qdrant:
# qdrant_url = http://localhost:6333?path=D:/qdrant_data/storage

directorio_archivo_json = ../data/SERVICIOS/ARCHIVOS
nombre_archivo_json = ServiciosPAMI.json

tamano_chunk = 300
overlap_chunk = 50
max_context_tokens = 80

collection_name_fragmento = fragment_store
```

## Diferencias Clave con la Versión Chroma

1. **Inicialización de la Base de Datos**:
   - Chroma: `Chroma(collection_name=collection_name, persist_directory=persist_directory, embedding_function=embeddings)`
   - Qdrant: `Qdrant(client=qdrant_client, collection_name=collection_name, embeddings=embeddings)`

2. **Cliente de Base de Datos**:
   - Chroma: No requiere un cliente separado
   - Qdrant: Requiere inicializar un cliente: `QdrantClient(url=qdrant_url)`

3. **Parámetros de Búsqueda**:
   - La búsqueda semántica en ambos casos usa `similarity_search_with_score()`, pero la configuración interna es diferente

## Cómo Ejecutar

### 1. Iniciar el Servidor FastAPI

Para iniciar el servidor FastAPI con el endpoint adaptado a Qdrant:

```bash
cd CARGA_BDV
uvicorn endpoint1_qdrant:app --host 0.0.0.0 --port 8000
```

### 2. Probar con el Cliente

```bash
python client_test_qdrant.py --endpoint complete --question "¿Cómo es la afiliación de la esposa de un afiliado?"
```

Parámetros disponibles:
- `--endpoint`: "simple" o "complete" (por defecto: "complete")
- `--question`: La pregunta a procesar
- `--k`: Número de documentos a recuperar (por defecto: 5)
- `--fecha-desde`: Fecha de inicio para filtrado (formato: YYYY-MM-DD)
- `--fecha-hasta`: Fecha de fin para filtrado (formato: YYYY-MM-DD)
- `--output`: Archivo para guardar la respuesta en formato JSON

## Estructura del Flujo

1. **Cliente** → Envía pregunta a través de HTTP
2. **Endpoint** → Recibe la pregunta y la procesa
3. **LangGraph** → Orquesta el flujo:
   - `query_or_respond` → Decide qué consulta realizar
   - `retrieve` → Recupera documentos relevantes desde Qdrant
   - `generate` → Genera la respuesta final
4. **Cliente** ← Recibe respuesta y metadatos

## Requisitos

- Python 3.8+
- FastAPI
- LangGraph
- Qdrant Client (`pip install qdrant-client`)
- LangChain con soporte para Qdrant (`pip install langchain-qdrant`)
- OpenAI API Key configurada en `config.ini` o como variable de entorno
- Servidor Qdrant corriendo en `http://localhost:6333` (o la URL especificada en `config.ini`)

## Ventajas de Qdrant sobre Chroma

- Mayor escalabilidad para grandes volúmenes de datos
- Mejor rendimiento en búsquedas con alto throughput
- Soporte nativo para filtrado avanzado
- API REST completa
- Opciones de despliegue más flexibles (standalone, Docker, clúster)
- Persistencia de datos más robusta 