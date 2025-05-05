# Adaptación a Qdrant

Este documento describe la adaptación del asistente virtual PAMI para utilizar Qdrant como base de datos vectorial en lugar de ChromaDB.

## Estructura del proyecto

El proyecto ha sido adaptado para usar Qdrant siguiendo la estructura de directorios existente:

```
app/
├── api/
│   └── endpoints.py     # Endpoints de la API actualizados para Qdrant
├── core/
│   ├── config.py        # Configuración adaptada para Qdrant
│   └── logging_config.py # Configuración de logging
├── models/
│   └── schemas.py       # Esquemas de datos para la API
├── services/
│   ├── graph_logic.py   # Lógica de grafos con LangGraph
│   ├── process_question.py # Servicio para procesar preguntas con Qdrant
│   └── token_utils.py   # Utilidades para manejo de tokens
├── static/
│   └── consulta_qdrant.html # Interfaz HTML para pruebas de Qdrant
└── main.py              # Aplicación FastAPI principal
```

## Cambios principales

1. **Configuración:** Se ha adaptado `app/core/config.py` para obtener la URL y nombre de colección de Qdrant desde el archivo de configuración.

2. **Procesamiento de preguntas:** Se ha implementado el servicio `app/services/process_question.py` para procesar preguntas usando Qdrant en lugar de ChromaDB.

3. **Endpoints de la API:** Se han actualizado los endpoints en `app/api/endpoints.py` para usar Qdrant como base de datos vectorial.

4. **Interfaz HTML:** Se ha creado una interfaz web en `app/static/consulta_qdrant.html` para probar las consultas a Qdrant.

5. **Cliente de prueba:** Se ha implementado un cliente de línea de comandos en `client_qdrant.py` para probar los endpoints desde la terminal.

## Configuración

La configuración para Qdrant se debe especificar en el archivo `config.ini` en la siguiente sección:

```ini
[SERVICIOS_SIMAP_Q]
qdrant_url = http://localhost:6333
collection_name_fragmento = fragment_store
nombre_bdvectorial = fragment_store
max_results = 5
```

## Uso

### Iniciar el servidor

```bash
cd tot17
uvicorn app.main:app --reload
```

### Probar desde el navegador

Acceder a la interfaz HTML de prueba:
```
http://localhost:8000/consulta
```

### Probar desde línea de comandos

```bash
python client_qdrant.py --question "¿Cómo es la afiliación de la esposa de un afiliado?" --k 5
```

Opciones disponibles:
- `--url`: URL base del servidor (default: http://localhost:8000)
- `--endpoint`: Tipo de endpoint a utilizar (simple o complete)
- `--question`: Pregunta a realizar
- `--k`: Número de documentos a recuperar
- `--fecha-desde`: Fecha desde la cual filtrar resultados (YYYY-MM-DD)
- `--fecha-hasta`: Fecha hasta la cual filtrar resultados (YYYY-MM-DD)
- `--output`: Archivo para guardar la respuesta

### Documentación de la API

La documentación interactiva de la API está disponible en:
```
http://localhost:8000/docs
```

## Requisitos

Asegúrate de tener instaladas las siguientes dependencias:

```bash
pip install fastapi uvicorn qdrant-client langchain-qdrant langchain-openai tiktoken langgraph
```

## Notas adicionales

- La adaptación mantiene la misma estructura de directorios y funcionalidad que la versión anterior con ChromaDB.
- Se ha añadido soporte para streaming de respuestas usando LangGraph.
- Se han mejorado los logs para incluir información sobre tokens y costos aproximados.
- La interfaz HTML permite seleccionar entre el endpoint simple y el de análisis completo. 