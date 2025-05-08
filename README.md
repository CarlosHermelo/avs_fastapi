# Asistente Virtual PAMI

Asistente virtual para responder preguntas sobre trámites y servicios de PAMI, utilizando una base de datos vectorial y modelos de lenguaje.

## Características

- API REST construida con FastAPI
- Procesamiento de consultas mediante LangGraph
- Base de datos vectorial con ChromaDB
- Respuestas contextuales basadas en información de PAMI
- Análisis de tokens para optimización de costos
- Logging detallado para seguimiento y depuración

## Estructura del Proyecto

```
.
├── app/                                # Directorio principal de la aplicación
│   ├── api/                            # Endpoints de la API
│   │   ├── endpoints.py                # Definición de rutas y controladores
│   │   └── __init__.py
│   ├── core/                           # Configuraciones y utilidades del núcleo
│   │   ├── config.py                   # Variables de configuración global
│   │   ├── logging_config.py           # Configuración de logging
│   │   └── __init__.py
│   ├── models/                         # Definición de modelos de datos
│   │   ├── schemas.py                  # Esquemas Pydantic para validación
│   │   └── __init__.py
│   ├── services/                       # Servicios y lógica de negocio
│   │   ├── process_question.py         # Procesamiento de preguntas
│   │   └── __init__.py
│   ├── main.py                         # Punto de entrada principal FastAPI
│   └── __init__.py
├── data/                               # Datos para la base vectorial (excluido de Git)
├── client_test.py                      # Cliente básico de prueba para la API
├── complete_client_test.py             # Cliente avanzado con más opciones
├── config.ini                          # Archivo de configuración
├── DOCKER.md                           # Guía detallada para Docker
├── Dockerfile                          # Configuración para construir imagen Docker
├── docker-compose.yml                  # Configuración para Docker Compose
├── frontend_client.html                # Cliente web HTML/JS
├── requirements.txt                    # Dependencias del proyecto
└── script_log.log                      # Archivo de logs (excluido de Git)
```

## Flujo del Proyecto

### 1. Arquitectura y Flujo de Datos

```
[frontend_client.html] o [client_test.py]
         ↓
[HTTP Request] → [app/main.py] → [app/api/endpoints.py]
         ↓
[app/services/process_question.py]
         ↓
[Base Vectorial ChromaDB] ← [data/]
         ↓
[LangGraph] → [Modelo OpenAI]
         ↓
[HTTP Response] → [Cliente]
```

### 2. Componentes Principales

#### Frontend (`frontend_client.html`)
- Interfaz web simple para enviar consultas
- Formulario con campos para:
  - Pregunta
  - Fecha desde
  - Fecha hasta
  - Cantidad de documentos (k)
- Realiza peticiones AJAX al endpoint `/complete_analysis`

#### Clientes de Prueba
- **client_test.py**: Cliente simple para el endpoint `/process_question`
- **complete_client_test.py**: Cliente avanzado para el endpoint `/complete_analysis`

#### Backend (FastAPI)
- **main.py**: Configuración de la aplicación FastAPI y middleware CORS
- **endpoints.py**: Define los endpoints REST:
  - `/process_question`: Procesa consultas básicas
  - `/complete_analysis`: Análisis completo con metadata

#### Procesamiento de Consultas
- **process_question.py**: Implementa el flujo de procesamiento:
  1. Recibe la consulta del usuario
  2. Vectoriza con OpenAI Embeddings
  3. Busca fragmentos relevantes en ChromaDB
  4. Genera respuesta con LangGraph
  5. Analiza y registra uso de tokens

#### Configuración
- **config.ini**: Archivo central con configuraciones:
  - API Key de OpenAI
  - Modelo a utilizar
  - Directorio de la base vectorial
  - Parámetros de búsqueda
  - Configuración de tokens

## Requisitos

- Python 3.9 o superior
- Docker y Docker Compose (opcional)
- API Key de OpenAI
- Conexión a Internet

## Configuración Inicial

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/pami-assistant.git
   cd pami-assistant
   ```

2. Crea un archivo `.env` con tu API Key de OpenAI:
   ```bash
   echo "OPENAI_API_KEY=tu-api-key" > .env
   ```

3. Asegúrate de tener la estructura correcta del directorio de fragmentos en `config.ini`.

4. Revisa y ajusta las configuraciones en `config.ini` según sea necesario:
   - `collection_name_fragmento`: Nombre de la colección en ChromaDB
   - `modelo`: Modelo de OpenAI a utilizar
   - `FRAGMENT_STORE_DIR`: Ruta al directorio de la base vectorial
   - `max_results`: Número máximo de resultados a devolver

## Ejecución

### Usando Docker (recomendado)

1. Construye y ejecuta los contenedores:
   ```bash
   docker-compose up -d
   ```

2. La API estará disponible en `http://localhost:8000`

### Sin Docker

1. Crea un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta la aplicación FastAPI con Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. La API estará disponible en `http://localhost:8000`

## Uso

### API REST

#### Endpoint para Procesar Preguntas
```bash
curl -X POST "http://localhost:8000/process_question" \
     -H "Content-Type: application/json" \
     -d '{
       "question_input": "¿Cómo afilio a mi pareja?", 
       "fecha_desde": "2024-01-01", 
       "fecha_hasta": "2024-12-31", 
       "k": 4
     }'
```

#### Endpoint para Análisis Completo
```bash
curl -X POST "http://localhost:8000/complete_analysis" \
     -H "Content-Type: application/json" \
     -d '{
       "question_input": "¿Cómo afilio a mi pareja?", 
       "fecha_desde": "2024-01-01", 
       "fecha_hasta": "2024-12-31", 
       "k": 4
     }'
```

### Cliente de Prueba en Línea de Comandos

Para ejecutar el cliente de prueba básico:
```bash
python client_test.py
```

Para el cliente avanzado con argumentos:
```bash
python complete_client_test.py "¿Cómo afilio a mi pareja?" 2024-01-01 2024-12-31 4
```

### Interfaz Web

1. Después de iniciar el servidor, abre el archivo `frontend_client.html` en un navegador web
2. Completa el formulario con tu consulta y parámetros
3. Presiona "Enviar Consulta" para obtener la respuesta

## Monitoreo y Logging

- Los logs se almacenan en `script_log.log`
- Contienen información detallada sobre:
  - Consultas procesadas
  - Documentos recuperados
  - Conteo de tokens
  - Costo aproximado de cada consulta

## Solución de Problemas

### Diferencia entre los endpoints

Esta aplicación ofrece dos endpoints principales:

1. **`/process_question`**: Endpoint original, más ligero pero con menos funcionalidades.
   - Puede tener problemas con recuperación de documentos en algunos casos
   - Devuelve solo la respuesta textual sin metadata

2. **`/complete_analysis`**: Endpoint más completo y robusto. Utilizado tanto por `client_test.py` como por `complete_client_test.py` y `frontend_client.html`.
   - Incluye metadata sobre el modelo usado y documentos recuperados
   - Tiene mejor manejo de errores y logging
   - Mejor rendimiento en consultas complejas

**Nota importante**: Por consistencia y mejor rendimiento, todos los clientes de ejemplo han sido configurados para usar el endpoint `/complete_analysis`. Si estás desarrollando tu propio cliente, te recomendamos usar este endpoint.

### Problemas comunes y soluciones

1. **Error "No tengo la información suficiente del SIMAP..."**:
   - **Causa**: La consulta no encontró documentos relevantes o el proceso de recuperación falló
   - **Solución**: 
     - Verifica que la base vectorial existe en la ruta especificada en `config.ini`
     - Prueba con el endpoint `/complete_analysis` que tiene mejor recuperación
     - Reformula la pregunta con términos más específicos

2. **Diferencias en resultados entre clientes**:
   - **Causa**: Los clientes usan diferentes endpoints con distinta implementación
   - **Solución**: Usa `complete_client_test.py` o `frontend_client.html` para consultas más precisas

3. **Problemas de conexión a ChromaDB**:
   - **Causa**: La base de datos vectorial no está accesible o no existe
   - **Solución**:
     - Verifica que el directorio `data/` existe y contiene los archivos de ChromaDB
     - Revisa el valor `FRAGMENT_STORE_DIR` en `config.ini`
     - Asegúrate de que la colección especificada existe

4. **Errores de API Key**:
   - **Causa**: La API Key de OpenAI no es válida o no está disponible
   - **Solución**:
     - Verifica la API Key en `config.ini` o en el archivo `.env`
     - Asegúrate de que la API Key tenga saldo y permisos suficientes

### Logs para diagnóstico

Para un diagnóstico más detallado, verifica los logs en:
- `script_log.log` - Logs generales de la aplicación
- Salida de consola al ejecutar con uvicorn - Contiene información de debug detallada

## Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add some amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## Licencia

Este proyecto está licenciado bajo [incluir licencia aquí].

# Gestión de Configuración y Secretos

## Variables de Entorno (Recomendado para Producción)

Para mejorar la seguridad, la aplicación ahora soporta la carga de configuración sensible a través de variables de entorno:

1. Crea un archivo `.env` en la raíz del proyecto (sólo para desarrollo, no incluirlo en Git):
   ```
   OPENAI_API_KEY=tu-api-key-aquí
   ENVIRONMENT=development
   ```

2. En producción, configura las variables de entorno usando los mecanismos de tu plataforma:
   - **Docker**: Usa `docker run -e OPENAI_API_KEY=valor ...` o `docker-compose.yml`
   - **Kubernetes**: Usa ConfigMaps/Secrets
   - **Servicios cloud**: Usa la configuración de variables de entorno del servicio

Las siguientes variables son compatibles:
- `OPENAI_API_KEY`: Tu clave API de OpenAI (obligatoria)
- `ENVIRONMENT`: Entorno de ejecución (development/production)
- `OPENAI_MODEL`: Modelo a utilizar (opcional)
- `QDRANT_URL`: URL del servidor Qdrant (opcional)
- `COLLECTION_NAME`: Nombre de la colección (opcional)
- `MAX_RESULTS`: Número máximo de resultados (opcional)

> **IMPORTANTE**: Las variables de entorno tienen prioridad sobre los valores en `config.ini`. En producción, se recomienda usar exclusivamente variables de entorno para la información sensible.

## Archivo de Configuración

El archivo `config.ini` sigue siendo compatible, pero no debe usarse para almacenar secretos en producción. Úsalo solo para configuraciones no sensibles. 