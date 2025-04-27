# Asistente Virtual PAMI

Asistente virtual para responder preguntas sobre trámites y servicios de PAMI, utilizando una base de datos vectorial y modelos de lenguaje.

## Características

- API REST construida con FastAPI
- Procesamiento de consultas mediante LangGraph
- Base de datos vectorial con ChromaDB
- Respuestas contextuales basadas en información de PAMI
- Análisis de tokens para optimización de costos
- Logging detallado para seguimiento y depuración

## Requisitos

- Python 3.9 o superior
- Docker y Docker Compose (opcional)
- API Key de OpenAI

## Configuración

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/pami-assistant.git
   cd pami-assistant
   ```

2. Crea un archivo `.env` con tu API Key de OpenAI:
   ```bash
   echo "OPENAI_API_KEY=tu-api-key" > .env
   ```

3. Asegúrate de tener la estructura correcta del directorio de fragmentos en tu archivo `config.ini`.

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

3. Ejecuta la aplicación:
   ```bash
   uvicorn app.main:app --reload
   ```

## Uso

### Endpoint básico

```bash
curl -X POST "http://localhost:8000/process_question" \
     -H "Content-Type: application/json" \
     -d '{"question_input": "¿Cómo afilio a mi pareja?", "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31", "k": 4}'
```

### Cliente de prueba

Para ejecutar el cliente de prueba:

```bash
python client_test.py
```

## Estructura del proyecto

```
.
├── app/
│   ├── api/
│   │   └── endpoints.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   └── process_question.py
│   └── main.py
├── config.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add some amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## Licencia

Este proyecto está licenciado bajo [incluir licencia aquí]. 