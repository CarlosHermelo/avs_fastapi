# app/core/config.py
import os
import configparser
from pathlib import Path
import re

# Buscar el archivo config.ini
def find_config_file():
    """
    Busca el archivo config.ini en varias ubicaciones posibles
    """
    possible_paths = [
        'config.ini',                   # En el directorio actual
        '../config.ini',                # En el directorio padre
        '../../config.ini',             # Dos niveles arriba
    ]
    
    # Buscar también a partir del directorio del script
    base_dir = Path(__file__).resolve().parent.parent.parent
    possible_paths.extend([
        str(base_dir / 'config.ini'),
        str(base_dir.parent / 'config.ini')
    ])
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError("No se pudo encontrar el archivo config.ini")

# Cargar la configuración
config = configparser.ConfigParser()
config_path = find_config_file()

# Leer el archivo de configuración manualmente para manejar API keys multilínea
with open(config_path, 'r') as f:
    content = f.read()

# Eliminar saltos de línea en la API key
fixed_content = re.sub(r'(openai_api_key\s*=\s*[^\n]+)\n([^\[=]+)', r'\1\2', content)

# Crear un archivo temporal con el contenido corregido
from io import StringIO
config.read_string(fixed_content)

# Configuración general
DEFAULT_SECTION = config['DEFAULT']
model_name = DEFAULT_SECTION.get('modelo', 'gpt-3.5-turbo')
openai_api_key = DEFAULT_SECTION.get('openai_api_key', os.environ.get('OPENAI_API_KEY', '')).strip()

# Imprimir los primeros 10 caracteres de la API key para debugging (no toda la key por seguridad)
api_key_prefix = openai_api_key[:10] if len(openai_api_key) > 10 else openai_api_key
print(f"API Key cargada (primeros caracteres): {api_key_prefix}...")

# Configuración de Qdrant
QDRANT_SECTION = config['SERVICIOS_SIMAP_Q']
qdrant_url = QDRANT_SECTION.get('qdrant_url', 'http://localhost:6333')
collection_name_fragmento = QDRANT_SECTION.get('collection_name_fragmento', 'fragment_store')
nombre_bdvectorial = QDRANT_SECTION.get('nombre_bdvectorial', 'fragment_store')
max_results = int(QDRANT_SECTION.get('max_results', 5))

# Para mantener compatibilidad con código que espera fragment_store_directory
fragment_store_directory = None  # Ya no se usa con Qdrant, pero lo mantenemos para compatibilidad

# Más configuraciones
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'filename': 'app.log',
            'encoding': 'utf-8',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
