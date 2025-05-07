# Migración de Chroma a Qdrant

Este conjunto de scripts permite migrar una base de datos vectorial de Chroma a Qdrant, manteniendo los mismos embeddings y metadatos.

## Requisitos

- Python 3.8+
- Qdrant (puede ser local o usando Docker)
- OpenAI API Key (para generar embeddings)
- Dependencias de Python:
  - qdrant-client
  - langchain-qdrant
  - langchain-openai
  - langchain

## Instalación

Puedes instalar Qdrant de dos formas: localmente (sin Docker) o usando Docker.

### Opción 1: Instalación local (sin Docker)

Este método es recomendado si no tienes Docker instalado o tienes problemas de espacio en disco.

```bash
# Ejecutar el asistente de instalación local
instalar_qdrant_local.bat
```

Este script te guiará a través de los siguientes pasos:
1. Seleccionar la unidad donde instalar Qdrant (puedes elegir cualquier unidad con suficiente espacio)
2. Instalar las dependencias necesarias de Python
3. Instalar el servidor Qdrant localmente
4. Configurar Qdrant para usar la unidad seleccionada
5. Crear un script para iniciar Qdrant fácilmente

Una vez instalado, debes:
1. Iniciar el servidor Qdrant con el script creado
2. Usar el parámetro `--qdrant-path` para especificar la ubicación de almacenamiento

### Opción 2: Instalación con Docker

Si prefieres usar Docker y tienes suficiente espacio disponible:

#### 1. Verificar e instalar dependencias automáticamente

```bash
python instalar_dependencias_qdrant.py
```

#### 2. Instalación manual de dependencias

```bash
pip install qdrant-client langchain-qdrant langchain-openai langchain
```

#### 3. Iniciar Qdrant con Docker

```bash
docker-compose -f docker-compose-qdrant.yml up -d
```

## Uso del script con parámetros adicionales

El script `carga_bdv_q1.py` ahora admite varios parámetros que te ayudarán a resolver problemas de espacio y a especificar diferentes ubicaciones:

```bash
# Modo prueba (carga solo 10 registros)
python carga_bdv_q1.py --modo-prueba

# Especificar una ruta alternativa para Qdrant
python carga_bdv_q1.py --qdrant-path=D:/mi_carpeta/qdrant_data

# Verificar espacio disponible antes de la carga
python carga_bdv_q1.py --comprobar-espacio

# Combinación de parámetros
python carga_bdv_q1.py --modo-prueba --qdrant-path=D:/qdrant_data --comprobar-espacio
```

## Configuración

### Archivo config.ini

La configuración se realiza a través del archivo `config.ini`. El script buscará automáticamente este archivo en las siguientes ubicaciones:

1. En el directorio actual
2. En el directorio padre
3. En el mismo directorio que el script
4. En el directorio padre del script

Se ha creado una nueva sección `[SERVICIOS_SIMAP_Q]` que contiene los parámetros necesarios para la conexión a Qdrant:

```ini
[SERVICIOS_SIMAP_Q]
# Configuración para la base de datos vectorial Qdrant
fecha_desde = 2024-02-08
fecha_hasta = 2024-12-10
max_results = 20

nombre_bdvectorial = servicios_simap_q
qdrant_url = http://localhost:6333

# Para especificar una ubicación específica para los datos de Qdrant:
# qdrant_url = http://localhost:6333?path=D:/qdrant_data/storage

# Formato DOCKER
directorio_archivo_json = data/json
nombre_archivo_json = servicios_simap.json

tamano_chunk = 300
overlap_chunk = 50
max_context_tokens = 80

collection_name_fragmento = fragment_store
```

## Scripts disponibles

### 1. carga_bdv_q1.py

Script principal para cargar datos desde un archivo JSON a Qdrant. Crea una nueva colección si no existe y carga los documentos con sus embeddings.

```bash
# Cargar todos los registros
python carga_bdv_q1.py

# Modo prueba (cargar solo 10 registros)
python carga_bdv_q1.py --modo-prueba

# Limitar a un número específico de registros
python carga_bdv_q1.py --limite 50

# Especificar ruta de almacenamiento alternativa para Qdrant
python carga_bdv_q1.py --qdrant-path=D:/qdrant_data/storage

# Verificar espacio antes de cargar
python carga_bdv_q1.py --comprobar-espacio
```

### 2. test_qdrant.py

Script de prueba para verificar la conexión y realizar búsquedas en la base de datos Qdrant.

```bash
python test_qdrant.py
```

### 3. instalar_dependencias_qdrant.py

Script utilitario para verificar e instalar las dependencias necesarias y comprobar la conexión con Qdrant.

```bash
python instalar_dependencias_qdrant.py
```

### 4. instalar_qdrant_local.bat

Script para instalar Qdrant localmente sin usar Docker. Útil si no tienes Docker o si tienes problemas de espacio.

```bash
instalar_qdrant_local.bat
```

### 5. liberar_espacio_sistema.bat

Script para verificar y liberar espacio en el sistema. Muestra información útil sobre las unidades y ofrece recomendaciones.

```bash
liberar_espacio_sistema.bat
```

## Modo de prueba

Para evitar largas esperas durante la carga inicial, puedes usar el modo prueba que cargará solo 10 registros:

```bash
python carga_bdv_q1.py --modo-prueba
```

Esto es útil para verificar rápidamente que todo funciona correctamente antes de hacer una carga completa.

## Migración desde Chroma

La migración desde Chroma a Qdrant mantiene la misma estructura de datos y metadatos:

1. Se utilizan los mismos embeddings (OpenAI)
2. Se mantienen los mismos metadatos (servicio, tipo, subtipo, id_sub)
3. Se añade una marca de tiempo en el metadato "fecha_carga"

## Funciones principales

- `cargar_json_a_qdrant`: Carga datos desde un archivo JSON a Qdrant
- `buscar_en_qdrant`: Realiza búsquedas semánticas en la base de datos
- `conectar_a_qdrant`: Conecta a una colección existente de Qdrant
- `cargar_configuracion`: Busca y carga el archivo config.ini desde múltiples ubicaciones

## Diferencias con Chroma

Qdrant ofrece algunas ventajas sobre Chroma:

- Mayor escalabilidad y rendimiento
- Más opciones de configuración y filtrado
- Soporte para búsquedas más complejas
- Mejor integración con Docker y entornos distribuidos
- Interfaz HTTP nativa (no requiere gRPC)

## Panel de administración de Qdrant

Una vez que Qdrant está en ejecución, puedes acceder a su panel de administración web en:

http://localhost:6333/dashboard

Este panel te permite:
- Ver todas las colecciones
- Explorar los puntos vectoriales
- Realizar búsquedas de prueba
- Verificar el estado del servidor

## Ejemplo de uso en código

```python
from carga_bdv_q1 import buscar_en_qdrant, conectar_a_qdrant, cargar_configuracion

# Cargar configuración
config = cargar_configuracion()
openai_api_key = config['DEFAULT']['openai_api_key']
url_qdrant = config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333')
collection_name = config['SERVICIOS_SIMAP_Q']['nombre_bdvectorial']

# Realizar una búsqueda
resultados = buscar_en_qdrant(
    query="¿cómo es la afiliación de la esposa de un afiliado?",
    openai_api_key=openai_api_key,
    url_qdrant=url_qdrant,
    collection_name=collection_name,
    max_results=5
)

# Procesar los resultados
for doc in resultados:
    print(f"Score: {doc['score']}")
    print(f"Servicio: {doc['metadata'].get('servicio')}")
    print(f"Contenido: {doc['contenido'][:100]}...")
```

## Resolución de problemas

### Error al encontrar el archivo config.ini

Si obtienes un error relacionado con el archivo config.ini:

1. El script busca el archivo en varias ubicaciones, pero si no lo encuentra, puedes colocarlo en:
   - El mismo directorio que el script `carga_bdv_q1.py`
   - En el directorio padre
   - Directamente en el directorio `CARGA_BDV`

2. Verifica que la sección `[SERVICIOS_SIMAP_Q]` existe en el archivo config.ini con todos los parámetros necesarios

### Error al encontrar el archivo JSON

Si obtienes un error indicando que no se encuentra el archivo JSON:

1. Verifica que la ruta configurada en `directorio_archivo_json` y `nombre_archivo_json` es correcta
2. El script intentará buscar el archivo en varias ubicaciones si no lo encuentra inicialmente
3. Puedes colocar el archivo JSON directamente en el directorio `data/json` o ajustar la ruta en el config.ini

### Error de espacio en disco insuficiente

Si obtienes un error como este:

```
Unexpected Response: 500 (Internal Server Error)
Raw response content:
b'{"status":{"error":"Service internal error: Espacio en disco insuficiente. (os error 112)"},"time":0.4505582}'
```

Esto indica que no hay suficiente espacio en disco para almacenar los datos.

#### Solución 1: Instalar Qdrant localmente en otra unidad

La mejor solución es instalar Qdrant localmente en una unidad con más espacio disponible:

```bash
instalar_qdrant_local.bat
```

Este script te permitirá seleccionar la unidad donde instalar Qdrant y configurará todo automáticamente.

#### Solución 2: Verificar y liberar espacio

```bash
liberar_espacio_sistema.bat
```

Este script muestra información sobre el espacio disponible y ofrece opciones para liberar espacio.

#### Solución 3: Usar parámetros de línea de comandos

Usa los nuevos parámetros para verificar el espacio y especificar una ubicación alternativa:

```bash
python carga_bdv_q1.py --modo-prueba --qdrant-path=D:/qdrant_data --comprobar-espacio
```

### Error de conexión con Qdrant

Si obtienes un error como "Connection refused" al intentar conectar con Qdrant:

1. Verifica que el servidor Qdrant esté en ejecución
   - Si instalaste localmente: ejecuta el script `iniciar_qdrant.bat` que se creó en la unidad seleccionada
   - Si usas Docker: verifica que el contenedor esté activo con `docker ps | grep qdrant`

2. Asegúrate de que el puerto 6333 no esté bloqueado por un firewall 