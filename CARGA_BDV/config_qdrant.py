# config_qdrant.py
import os
import configparser

# Cargar configuración
def cargar_configuracion():
    """
    Carga la configuración desde config.ini
    """
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

def obtener_config_qdrant():
    """
    Obtiene la configuración específica para Qdrant
    """
    config = cargar_configuracion()
    
    # Verificar que existe la sección de SERVICIOS_SIMAP_Q
    if 'SERVICIOS_SIMAP_Q' not in config:
        raise ValueError("La sección SERVICIOS_SIMAP_Q no existe en el archivo config.ini")
    
    # Parámetros de Qdrant
    config_data = {
        'openai_api_key': config['DEFAULT']['openai_api_key'],
        'modelo': config['DEFAULT'].get('modelo', 'gpt-4o-mini'),
        'qdrant_url': config['SERVICIOS_SIMAP_Q'].get('qdrant_url', 'http://localhost:6333'),
        'collection_name': config['SERVICIOS_SIMAP_Q'].get('collection_name_fragmento', 'fragment_store'),
        'nombre_bdvectorial': config['SERVICIOS_SIMAP_Q'].get('nombre_bdvectorial', 'fragment_store'),
        'max_results': int(config['SERVICIOS_SIMAP_Q'].get('max_results', 5))
    }
    
    return config_data

if __name__ == "__main__":
    # Prueba de la configuración
    try:
        config = obtener_config_qdrant()
        print("Configuración cargada correctamente:")
        for key, value in config.items():
            if key == 'openai_api_key':
                # Ocultar la clave API por seguridad
                value = value[:8] + "..." + value[-4:]
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Error al cargar la configuración: {str(e)}") 