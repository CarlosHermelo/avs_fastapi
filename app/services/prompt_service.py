# app/services/prompt_service.py
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

# Obtener el logger
logger = logging.getLogger(__name__)

# Prompt por defecto hardcodeado
DEFAULT_PROMPT = "Hola, soy tu asistente. ¿En qué puedo ayudarte?"

def get_database_engine():
    """
    Crea y retorna un motor de base de datos.
    Intenta primero con MySQL y si falla, usa SQLite.
    """
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    # Intentar con MySQL si está configurado
    if db_type.lower() == "mysql":
        try:
            db_host = os.getenv("BD_SERVER", "localhost")
            db_port = os.getenv("BD_PORT", "3306")
            db_name = os.getenv("BD_NAME", "avsp")
            db_user = os.getenv("BD_USER", "root")
            db_pass = os.getenv("BD_PASSWD", "")
            
            database_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
            
            engine = create_engine(
                database_url,
                pool_recycle=3600,
                pool_pre_ping=True,
                connect_args={
                    "connect_timeout": 60,
                    "sql_mode": "NO_AUTO_VALUE_ON_ZERO"
                }
            )
            
            # Probar la conexión
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info(f"Conexión a MySQL exitosa para obtener prompt")
                return engine
                
        except Exception as e:
            logger.warning(f"Error al conectar con MySQL para prompt: {e}")
            logger.info("Intentando con SQLite como alternativa...")
    
    # Usar SQLite como fallback
    try:
        # Construir la ruta del archivo SQLite
        project_root = Path(__file__).resolve().parent.parent.parent
        sqlite_path = os.getenv("SQLITE_PATH")
        
        if not sqlite_path:
            sqlite_path = project_root / "BD_RELA" / "local_database.db"
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
        
        sqlite_url = f"sqlite:///{sqlite_path}"
        engine = create_engine(sqlite_url)
        
        # Probar la conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info(f"Conexión a SQLite exitosa para obtener prompt: {sqlite_path}")
            return engine
            
    except Exception as e:
        logger.error(f"Error al conectar con SQLite para prompt: {e}")
        return None

def get_active_prompt_from_db():
    """
    Obtiene el prompt activo desde la base de datos.
    Retorna una tupla (contenido_prompt, id_prompt) o (None, None) si no se encuentra.
    """
    try:
        engine = get_database_engine()
        if not engine:
            logger.error("No se pudo establecer conexión a la base de datos para obtener prompt")
            return None, None
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Buscar prompt activo con su ID
            result = session.execute(
                text("SELECT contenido_prompt, id_prompt FROM prompts WHERE activo = :activo LIMIT 1"),
                {"activo": True}
            )
            
            row = result.fetchone()
            if row:
                prompt_content = row[0]
                id_prompt = row[1]
                logger.info(f"Prompt obtenido desde base de datos - ID: {id_prompt}")
                return prompt_content, int(id_prompt)
            else:
                logger.warning("No se encontró ningún prompt activo en la base de datos")
                return None, None
                
        except Exception as e:
            logger.error(f"Error al consultar prompt en la base de datos: {e}")
            return None, None
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error general al obtener prompt desde base de datos: {e}")
        return None, None

def get_prompt_from_file():
    """
    Obtiene el prompt desde el archivo prompt_fallback.txt.
    Retorna una tupla (contenido, nombre_archivo) o (None, None) si no se puede leer.
    """
    try:
        # Buscar el archivo en varias ubicaciones posibles
        project_root = Path(__file__).resolve().parent.parent.parent
        possible_paths = [
            project_root / "prompt_fallback.txt",
            Path("prompt_fallback.txt"),
            Path("../prompt_fallback.txt"),
            Path("../../prompt_fallback.txt")
        ]
        
        for file_path in possible_paths:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            file_name = file_path.name
                            logger.info(f"Prompt obtenido desde archivo: {file_path}")
                            return content, file_name
                except Exception as e:
                    logger.error(f"Error al leer archivo {file_path}: {e}")
                    continue
        
        logger.error("No se pudo encontrar o leer el archivo prompt_fallback.txt")
        return None, None
        
    except Exception as e:
        logger.error(f"Error general al obtener prompt desde archivo: {e}")
        return None, None

def get_system_prompt():
    """
    Obtiene el prompt del sistema siguiendo la jerarquía de fallbacks:
    1. Base de datos (prompt activo)
    2. Archivo prompt_fallback.txt
    3. Prompt hardcodeado por defecto
    
    Retorna una tupla (contenido_prompt, fuente, identificador) donde:
    - contenido_prompt: El texto del prompt
    - fuente: "base_de_datos", "archivo_txt", o "constante_hardcodeada"
    - identificador: ID del prompt (número para BD), nombre archivo para txt, None para constante
    """
    # Intentar obtener desde base de datos
    prompt_content, id_prompt = get_active_prompt_from_db()
    if prompt_content:
        logger.info("PROMPT_SOURCE: Desde base de datos")
        return prompt_content, "base_de_datos", id_prompt
    
    # Intentar obtener desde archivo
    prompt_content, file_name = get_prompt_from_file()
    if prompt_content:
        logger.info("PROMPT_SOURCE: Desde archivo prompt_fallback.txt")
        return prompt_content, "archivo_txt", file_name
    
    # Usar prompt hardcodeado como último recurso
    logger.warning("PROMPT_SOURCE: Usando prompt hardcodeado por defecto")
    return DEFAULT_PROMPT, "constante_hardcodeada", None 