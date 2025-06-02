# app/core/logging_config.py
import logging
import os
import datetime
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Configurar el directorio de logs (SIEMPRE usar la carpeta logs)
try:
    # Obtener el directorio base (raíz del proyecto)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Directorio base: {base_dir}")
    
    # Directorio de logs principal - FORZAR siempre logs/
    log_dir = os.path.join(base_dir, 'logs')
    print(f"Directorio de logs: {log_dir}")
    
    # SIEMPRE crear el directorio de logs, no hay directorio alternativo
    os.makedirs(log_dir, exist_ok=True)
    print(f"Directorio de logs creado/verificado en: {log_dir}")
    
    # Verificar permisos de escritura en el directorio de logs
    test_file_path = os.path.join(log_dir, 'test_write.tmp')
    try:
        with open(test_file_path, 'w') as f:
            f.write('test')
        os.remove(test_file_path)
        print(f"Permisos de escritura verificados en: {log_dir}")
    except Exception as e:
        print(f"ERROR: Sin permisos de escritura en {log_dir}: {str(e)}")
        # FORZAR la creación del directorio con permisos
        try:
            os.makedirs(log_dir, mode=0o755, exist_ok=True)
            print(f"Directorio de logs recreado con permisos en: {log_dir}")
        except Exception as e2:
            print(f"ERROR CRÍTICO: No se puede crear directorio de logs: {str(e2)}")
            raise Exception(f"No se puede configurar logging en {log_dir}")
        
except Exception as e:
    print(f"ERROR al configurar directorio de logs: {str(e)}")
    traceback.print_exc()
    # NUNCA usar el directorio actual como fallback
    # En su lugar, usar una carpeta logs en el directorio de trabajo actual
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    print(f"Usando directorio de logs en CWD: {log_dir}")

# Archivo de log con fecha específica
log_date = datetime.datetime.now().strftime("%Y%m%d")
log_file = os.path.join(log_dir, f'app_{log_date}.log')
debug_log_file = os.path.join(log_dir, f'debug_{log_date}.log')

print(f"Archivo de log configurado en: {log_file}")
print(f"Archivo de debug configurado en: {debug_log_file}")

# Configurar el logger principal
def setup_logger():
    """Configurar el logger principal de la aplicación"""
    # Logger principal
    logger = logging.getLogger('app')
    logger.setLevel(logging.INFO)
    
    # Evitar duplicación de handlers
    if logger.handlers:
        print("Limpiando handlers existentes para evitar duplicación")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Configurar el formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Intentar configurar el file handler principal
    try:
        # Escribir un archivo directo para diagnóstico
        with open(debug_log_file, 'a') as f:
            f.write(f"{datetime.datetime.now()} - Inicializando logger\n")
        
        # Configurar el file handler para el archivo principal
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        print(f"Handler de archivo configurado correctamente en: {log_file}")
        
        # Escribir confirmación de inicialización
        with open(log_file, 'a') as f:
            f.write(f"\n\n{'='*50}\n")
            f.write(f"{datetime.datetime.now()} - LOGGER INICIALIZADO\n")
            f.write(f"{'='*50}\n\n")
            
    except Exception as e:
        print(f"ERROR al configurar file handler: {str(e)}")
        traceback.print_exc()
        # Si no se puede crear el log file, fallar completamente
        raise Exception(f"No se puede configurar el logging correctamente: {str(e)}")
    
    # Configurar el console handler (siempre funcionará)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Inicializar el logger
try:
    logger = setup_logger()
    print("Logger configurado correctamente")
except Exception as e:
    print(f"ERROR crítico al configurar logger: {str(e)}")
    traceback.print_exc()
    # Configurar un logger básico si todo falla
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('app')

def log_message(message, level='INFO'):
    """
    Función para loguear mensajes con el nivel especificado
    """
    try:
        if level == 'ERROR':
            logger.error(message)
        elif level == 'WARNING':
            logger.warning(message)
        elif level == 'DEBUG':
            logger.debug(message)
        else:
            logger.info(message)
            
        # Además, guardar en el archivo de debug para diagnóstico
        with open(debug_log_file, 'a') as f:
            f.write(f"{datetime.datetime.now()} - {level} - {message}\n")
            
    except Exception as e:
        print(f"ERROR al hacer log: {str(e)} - Mensaje: {message}")

def get_logger():
    """
    Retorna el logger principal
    """
    return logger

# Registrar inicio del logger
log_message("=== INICIO DE LOGGING ===")
log_message(f"Logger configurado en: {log_file}")
log_message(f"Debug log configurado en: {debug_log_file}")

