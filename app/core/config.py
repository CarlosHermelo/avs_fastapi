# app/core/config.py
import os
import configparser
from pathlib import Path
import re

# Intentar cargar variables de entorno desde .env si existe, con override para asegurar que se recarguen siempre
try:
    from dotenv import load_dotenv, find_dotenv
    dotenv_path = find_dotenv()
    if dotenv_path:
        print(f"Cargando variables de entorno desde: {dotenv_path}")
        load_dotenv(dotenv_path, override=True)  # Cargar forzando override de variables existentes
    else:
        print("Archivo .env no encontrado")
except ImportError:
    # dotenv no está instalado, continuamos sin él
    print("python-dotenv no está instalado, no se cargarán variables desde .env")
    pass

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

# Cargar la configuración desde archivo si existe
config = configparser.ConfigParser()
try:
    config_path = find_config_file()
    print(f"Cargando configuración desde: {config_path}")
    
    # Leer el archivo de configuración manualmente para manejar API keys multilínea y BOM
    with open(config_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Eliminar saltos de línea en la API key
    fixed_content = re.sub(r'(openai_api_key\s*=\s*[^\n]+)\n([^\[=]+)', r'\1\2', content)
    
    # Cargar la configuración
    config.read_string(fixed_content)
except FileNotFoundError:
    # No se encontró config.ini, usaremos solo variables de entorno
    print("Archivo config.ini no encontrado, usando solo variables de entorno")
    pass

# Configuración general - Accediendo correctamente a las secciones
model_name = os.environ.get('OPENAI_MODEL', '')
if not model_name and 'DEFAULT' in config:
    model_name = config['DEFAULT'].get('modelo', 'gpt-3.5-turbo')

# Priorizar la variable de entorno para la API key, pero usar config.ini como fallback
openai_api_key = os.environ.get('OPENAI_API_KEY', '')

# Mostrar la API key que se está usando (solo primeros y últimos caracteres)
if openai_api_key:
    key_preview = f"{openai_api_key[:5]}...{openai_api_key[-4:]}" if len(openai_api_key) > 9 else openai_api_key
    print(f"Usando OPENAI_API_KEY desde variables de entorno: {key_preview}")
elif 'DEFAULT' in config:
    openai_api_key = config['DEFAULT'].get('openai_api_key', '').strip()
    key_preview = f"{openai_api_key[:5]}...{openai_api_key[-4:]}" if len(openai_api_key) > 9 else openai_api_key
    print(f"Usando OPENAI_API_KEY desde config.ini: {key_preview}")

# API Keys adicionales desde config.ini
tavily_api_key = ''
cohere_api_key = ''
if 'DEFAULT' in config:
    tavily_api_key = config['DEFAULT'].get('tavily_api_key', '')
    cohere_api_key = config['DEFAULT'].get('cohere_api_key', '')

# Solo mostrar información sensible en entorno de desarrollo
if openai_api_key and os.environ.get('ENVIRONMENT', '').lower() != 'production':
    api_key_prefix = openai_api_key[:5] if len(openai_api_key) > 5 else openai_api_key
    print(f"API Key cargada (primeros caracteres): {api_key_prefix}...")

# Configuración de Qdrant
if 'SERVICIOS_SIMAP_Q' in config:
    qdrant_url = os.environ.get('QDRANT_URL', config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333'))
    collection_name_fragmento = os.environ.get('COLLECTION_NAME', config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store'))
    nombre_bdvectorial = os.environ.get('NOMBRE_BDV', config['SERVICIOS_SIMAP_Q'].get('nombre_bdvectorial', 'fragment_store'))
    max_results = int(os.environ.get('MAX_RESULTS', config['SERVICIOS_SIMAP_Q'].get('max_results', 5)))
else:
    qdrant_url = os.environ.get('QDRANT_URL', 'http://localhost:6333')
    collection_name_fragmento = os.environ.get('COLLECTION_NAME', 'fragment_store')
    nombre_bdvectorial = os.environ.get('NOMBRE_BDV', 'fragment_store')
    max_results = int(os.environ.get('MAX_RESULTS', 5))

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
