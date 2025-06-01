import sys # Asegurarse de que sys está importado
import os # Asegurarse de que os está importado

# Añadir el directorio raíz del proyecto a sys.path
# Esto permite que el script encuentre el módulo 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
import time
import traceback
from sqlalchemy import create_engine, text, text, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
# from app.core.logging_config import log_message, get_logger # Comentamos o eliminamos esta línea si solo se usaba para get_engine

# Cargar variables de entorno
load_dotenv()

# Obtener información de conexión
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # Por defecto usa sqlite
DB_HOST = os.getenv("BD_SERVER", "localhost")
DB_PORT = os.getenv("BD_PORT", "3306")
DB_NAME = os.getenv("BD_NAME", "avsp")
DB_USER = os.getenv("BD_USER", "root")
DB_PASS = os.getenv("BD_PASSWD", "")

# Ruta para la base SQLite - CONSTRUCCIÓN MEJORADA
DEFAULT_SQLITE_FILENAME = "local_database.db"
SQLITE_DIR_RELATIVE_TO_ROOT = "BD_RELA" # Directorio donde queremos el sqlite, relativo a la raíz del proyecto

# Primero, intenta obtener la ruta completa desde la variable de entorno .env
SQLITE_PATH_FROM_ENV = os.getenv("SQLITE_PATH")

if SQLITE_PATH_FROM_ENV:
    SQLITE_PATH = SQLITE_PATH_FROM_ENV
    # print(f"Usando SQLITE_PATH desde .env: {SQLITE_PATH}") # Log de depuración opcional
else:
    # Si no está en .env, construir la ruta relativa a la raíz del proyecto detectada (project_root)
    SQLITE_PATH = os.path.join(project_root, SQLITE_DIR_RELATIVE_TO_ROOT, DEFAULT_SQLITE_FILENAME)
    # print(f"SQLITE_PATH no encontrado en .env. Usando ruta por defecto construida: {SQLITE_PATH}") # Log de depuración opcional

# Crear metadata y base declarativa
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Variable para almacenar el tipo de motor actualmente en uso
current_engine_type = None

def get_engine():
    """Crea y retorna un motor de base de datos.
    Intenta primero con MySQL y si falla, usa SQLite."""
    global current_engine_type
    
    # Probar primero con MySQL si está configurado para ello
    if DB_TYPE.lower() == "mysql":
        try:
            print(f"Intentando conectar a MySQL en {DB_HOST}:{DB_PORT}...")
            # Construir URL de conexión para MySQL
            DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
            
            engine = create_engine(
                DATABASE_URL,
                pool_recycle=3600,
                pool_pre_ping=True,
                connect_args={
                    "connect_timeout": 60,
                    "sql_mode": "NO_AUTO_VALUE_ON_ZERO"
                }
            )
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print(f"Conexión a MySQL ({DB_NAME}@{DB_HOST}) exitosa.")
                
            current_engine_type = "mysql"
            return engine
        except Exception as e:
            print(f"Error al conectar con MySQL ({DB_NAME}@{DB_HOST}): {e}")
            print("Intentando con SQLite como alternativa...")
    
    # Si falla MySQL o está configurado para SQLite, usar SQLite
    print(f"Usando SQLite en {SQLITE_PATH}")
    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    
    os.makedirs(os.path.dirname(os.path.abspath(SQLITE_PATH)), exist_ok=True)
    
    engine = create_engine(sqlite_url)
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    current_engine_type = "sqlite"
    print(f"Conexión a SQLite ({SQLITE_PATH}) establecida.")
    return engine

# Definir modelos
class Usuario(Base):
    __tablename__ = "usuarios"
    
    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    ugel_origen = Column(String(100))

class Prompt(Base):
    __tablename__ = "prompts"
    
    id_prompt = Column(Integer, primary_key=True, autoincrement=True)
    nombre_prompt = Column(String(100), nullable=False)
    contenido_prompt = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    activo = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.now)

class Consulta(Base):
    __tablename__ = "consultas"
    
    id_consulta = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    
    # Información del usuario - SIN FOREIGN KEY CONSTRAINT
    # Los datos vienen directamente del HTML y no necesitan validación en BD
    id_usuario = Column(Integer, nullable=False)  # Eliminada ForeignKey("usuarios.id_usuario")
    ugel_origen = Column(String(100))
    
    # Contenido de la interacción
    pregunta_usuario = Column(Text, nullable=False)
    respuesta_asistente = Column(Text)
    respuesta_es_vacia = Column(Boolean, default=False)
    # En SQLite no hay ENUM, así que usamos String
    respuesta_util = Column(String(15), default="sin feedback")
    
    # Información técnica - SIN FK con prompts para simplificar
    id_prompt_usado = Column(String(100))  # Cambiado a String para almacenar nombre/id sin FK
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    tiempo_respuesta_ms = Column(Integer)
    
    # NUEVOS CAMPOS AGREGADOS
    version_prompt = Column(String(100))  # Versión del prompt utilizado
    comentario = Column(String(255))      # Campo para comentarios adicionales
    
    # Estado de ejecución
    error_detectado = Column(Boolean, default=False)
    tipo_error = Column(String(100))
    mensaje_error = Column(Text)
    
    # Campos opcionales
    origen_canal = Column(String(50))
    modelo_llm_usado = Column(String(100))
    
    # Relaciones - ELIMINADAS para evitar foreign keys
    # usuario = relationship("Usuario")  # ELIMINADO
    # prompt = relationship("Prompt")    # ELIMINADO

class FeedbackRespuesta(Base):
    __tablename__ = "feedback_respuesta"
    
    id_feedback = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("consultas.id_consulta"), nullable=False)
    # Información del usuario - SIN FOREIGN KEY CONSTRAINT
    # Los datos vienen directamente del HTML y no necesitan validación en BD
    id_usuario = Column(Integer, nullable=False)  # Eliminada ForeignKey("usuarios.id_usuario")
    # En SQLite no hay ENUM, así que usamos String
    utilidad_respuesta = Column(String(10))
    comentario = Column(Text)
    fecha = Column(DateTime, default=datetime.now)
    
    # Relaciones - SOLO con consultas, no con usuarios
    consulta = relationship("Consulta")
    # usuario = relationship("Usuario")  # ELIMINADO

class LogBatchBDV(Base):
    __tablename__ = "log_batch_bdv"
    
    id_batch = Column(Integer, primary_key=True, autoincrement=True)
    fecha_ejecucion = Column(DateTime, default=datetime.now)
    json_generado = Column(Boolean, default=False)
    carga_exitosa = Column(Boolean, default=False)
    estado_bdv = Column(String(100))
    mensaje_log = Column(Text)

class LogArranqueApp(Base):
    __tablename__ = "log_arranque_app"
    
    id_arranque = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    bd_vectorial_ok = Column(Boolean)
    bd_relacional_ok = Column(Boolean)
    mensaje_error = Column(Text)

def crear_tablas():
    """Crea las tablas en la base de datos."""
    try:
        # Obtener motor de base de datos (MySQL o SQLite)
        engine = get_engine()
        
        # Informar sobre el tipo de base de datos en uso
        print(f"Usando base de datos: {current_engine_type.upper()}")
        
        # Configuración específica para MySQL
        if current_engine_type == "mysql":
            try:
                # Desactivar verificación de claves foráneas temporalmente
                with engine.connect() as conn:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                    conn.commit()
                    print("Verificación de claves foráneas desactivada temporalmente.")
            except Exception as e:
                print(f"Aviso: {e}")
                print("No se pudo desactivar la verificación de claves foráneas. Intentando con otro método...")
                try:
                    # Alternativa usando execute con connection directa
                    connection = engine.raw_connection()
                    cursor = connection.cursor()
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                    connection.commit()
                    print("Verificación de claves foráneas desactivada con método alternativo.")
                except Exception as e2:
                    print(f"Error al desactivar claves foráneas: {e2}")
        
        # Eliminar tablas si existen en orden inverso a las dependencias
        print("\nEliminando tablas existentes para recrearlas...")
        for tabla in reversed([FeedbackRespuesta, Consulta, Usuario, Prompt, LogBatchBDV, LogArranqueApp]):
            tabla_nombre = tabla.__tablename__
            try:
                tabla.__table__.drop(engine, checkfirst=True)
                print(f"Tabla '{tabla_nombre}' eliminada si existía.")
            except Exception as e:
                print(f"Nota al eliminar '{tabla_nombre}': {e}")
                print(f"Intentando eliminar '{tabla_nombre}' con SQL directo...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"DROP TABLE IF EXISTS {tabla_nombre}"))
                        conn.commit()
                        print(f"Tabla '{tabla_nombre}' eliminada con SQL directo.")
                except Exception as e2:
                    print(f"No se pudo eliminar '{tabla_nombre}': {e2}")
        
        # Crear tablas en orden específico para manejar claves foráneas
        print("\nCreando tablas...")
        
        # Primero crear tablas sin dependencias
        for tabla in [Usuario, Prompt, LogBatchBDV, LogArranqueApp]:
            tabla_nombre = tabla.__tablename__
            try:
                tabla.__table__.create(engine, checkfirst=True)
                print(f"Tabla '{tabla_nombre}' creada exitosamente.")
                time.sleep(0.2)  # Pequeña pausa
            except Exception as e:
                print(f"Error al crear la tabla '{tabla_nombre}': {e}")
                raise
        
        # Luego crear tablas con dependencias
        for tabla in [Consulta, FeedbackRespuesta]:
            tabla_nombre = tabla.__tablename__
            try:
                tabla.__table__.create(engine, checkfirst=True)
                print(f"Tabla '{tabla_nombre}' creada exitosamente.")
                time.sleep(0.2)  # Pequeña pausa
            except Exception as e:
                print(f"Error al crear la tabla '{tabla_nombre}': {e}")
                raise
        
        # Reactivar verificación de claves foráneas para MySQL
        if current_engine_type == "mysql":
            try:
                with engine.connect() as conn:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                    conn.commit()
                    print("Verificación de claves foráneas reactivada.")
            except Exception as e:
                print(f"Aviso: {e}")
                try:
                    # Alternativa usando execute con connection directa
                    connection = engine.raw_connection()
                    cursor = connection.cursor()
                    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                    connection.commit()
                    print("Verificación de claves foráneas reactivada con método alternativo.")
                except Exception as e2:
                    print(f"Error al reactivar claves foráneas: {e2}")
        
        print("\nProceso finalizado. Todas las tablas han sido creadas con claves foráneas.")
        
        # Crear y retornar una sesión para su uso (opcional)
        Session = sessionmaker(bind=engine)
        return Session()
        
    except Exception as e:
        print(f"Error general al crear las tablas: {e}")
        traceback.print_exc()
        return None

def crear_datos_prueba(session):
    """Crea algunos datos de prueba en la base de datos."""
    if not session:
        print("No se pudo crear sesión para insertar datos de prueba.")
        return
    
    try:
        # Crear usuarios de prueba
        usuario1 = Usuario(nombre="Usuario Prueba 1", ugel_origen="UGEL 01")
        usuario2 = Usuario(nombre="Usuario Prueba 2", ugel_origen="UGEL 02")
        session.add_all([usuario1, usuario2])
        
        # Crear prompts de prueba
        prompt1 = Prompt(
            nombre_prompt="Prompt Básico", 
            contenido_prompt="Este es un prompt de prueba",
            version=1,
            activo=True
        )
        session.add(prompt1)
        
        # Confirmar cambios
        session.commit()
        print("Datos de prueba creados exitosamente.")
        
    except Exception as e:
        session.rollback()
        print(f"Error al crear datos de prueba: {e}")

if __name__ == "__main__":
    print("Iniciando creación de tablas...")
    session = crear_tablas()
    
    # Crear datos de prueba si el parámetro --test está presente
    if "--test" in sys.argv:
        print("\nCreando datos de prueba...")
        crear_datos_prueba(session)
    
    # Cerrar sesión si se creó
    if session:
        session.close() 