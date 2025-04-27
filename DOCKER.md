# Guía de Docker para Asistente PAMI

Este documento proporciona instrucciones detalladas para ejecutar la aplicación utilizando Docker.

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado
- API Key de OpenAI

## Configuración

1. Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
   ```
   OPENAI_API_KEY=tu-api-key-de-openai
   ```

2. Si necesitas personalizar la configuración, edita el archivo `config.ini`.

## Construir y ejecutar la aplicación

### Opción 1: Usando Docker Compose (recomendado)

1. Construye y ejecuta los contenedores:
   ```bash
   docker-compose up -d
   ```

2. Para ver los logs:
   ```bash
   docker-compose logs -f
   ```

3. Para detener los contenedores:
   ```bash
   docker-compose down
   ```

### Opción 2: Usando Docker directamente

1. Construye la imagen:
   ```bash
   docker build -t pami-assistant .
   ```

2. Ejecuta el contenedor:
   ```bash
   docker run -d -p 8000:8000 --name pami-assistant --env-file .env pami-assistant
   ```

3. Para ver los logs:
   ```bash
   docker logs -f pami-assistant
   ```

4. Para detener el contenedor:
   ```bash
   docker stop pami-assistant
   docker rm pami-assistant
   ```

## Verificar que la aplicación está funcionando

1. La API estará disponible en `http://localhost:8000`

2. Puedes probar la API con curl:
   ```bash
   curl -X POST "http://localhost:8000/process_question" \
        -H "Content-Type: application/json" \
        -d '{"question_input": "¿Cómo afilio a mi pareja?", "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31", "k": 4}'
   ```

## Solución de problemas

### La aplicación no se inicia

1. Verifica los logs:
   ```bash
   docker-compose logs -f
   ```

2. Asegúrate de que la API Key de OpenAI es válida y está correctamente configurada en el archivo `.env`.

3. Comprueba que los volúmenes están correctamente configurados en `docker-compose.yml`.

### Errores de memoria

Si la aplicación consume demasiada memoria, puedes limitar los recursos:

```yaml
services:
  app:
    # ... otras configuraciones
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
```

### Problemas de permisos

Si encuentras problemas de permisos en los volúmenes:

```bash
# Cambia el propietario de los archivos al usuario que ejecuta Docker
sudo chown -R $(id -u):$(id -g) ./app
```

## Construir para producción

Para un entorno de producción, considera:

1. Usar una imagen más pequeña como alpine:
   ```dockerfile
   FROM python:3.9-alpine
   ```

2. Configurar redes Docker personalizadas para mayor seguridad.

3. Implementar un proxy reverso como Nginx para manejar SSL y caché.

4. Usar secretos de Docker para gestionar la API Key en lugar de variables de entorno:
   ```yaml
   services:
     app:
       secrets:
         - openai_api_key
   
   secrets:
     openai_api_key:
       file: ./openai_api_key.txt
   ``` 