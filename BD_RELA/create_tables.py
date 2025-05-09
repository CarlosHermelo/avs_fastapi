from dotenv import load_dotenv
import os
import sys
import time
import traceback
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Obtener información de conexión
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # Por defecto usa sqlite
DB_HOST = os.getenv("BD_SERVER", "localhost")
DB_PORT = os.getenv("BD_PORT", "3306")
DB_NAME = os.getenv("BD_NAME", "avsp")
DB_USER = os.getenv("BD_USER", "root")
DB_PASS = os.getenv("BD_PASSWD", "")
# Ruta para la base SQLite
SQLITE_PATH = os.getenv("SQLITE_PATH", "BD_RELA/local_database.db")

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
            
            # Crear motor para MySQL
            engine = create_engine(
                DATABASE_URL,
                pool_recycle=3600,
                pool_pre_ping=True,
                connect_args={
                    "connect_timeout": 60,
                    "sql_mode": "NO_AUTO_VALUE_ON_ZERO"
                }
            )
            
            # Verificar la conexión
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                print("Conexión a MySQL exitosa.")
                
            current_engine_type = "mysql"
            return engine
        except Exception as e:
            print(f"Error al conectar con MySQL: {e}")
            print("Intentando con SQLite como alternativa...")
    
    # Si falla MySQL o está configurado para SQLite, usar SQLite
    print(f"Usando SQLite en {SQLITE_PATH}")
    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    
    # Crear el directorio para el archivo de base de datos si no existe
    os.makedirs(os.path.dirname(os.path.abspath(SQLITE_PATH)), exist_ok=True)
    
    # Crear motor SQLite
    engine = create_engine(sqlite_url)
    
    # Configuración para habilitar claves foráneas en SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    current_engine_type = "sqlite"
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
    
    # Información del usuario
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    ugel_origen = Column(String(100))
    
    # Contenido de la interacción
    pregunta_usuario = Column(Text, nullable=False)
    respuesta_asistente = Column(Text)
    respuesta_es_vacia = Column(Boolean, default=False)
    # En SQLite no hay ENUM, así que usamos String
    respuesta_util = Column(String(15), default="sin feedback")
    
    # Información técnica
    id_prompt_usado = Column(Integer, ForeignKey("prompts.id_prompt"))
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    tiempo_respuesta_ms = Column(Integer)
    
    # Estado de ejecución
    error_detectado = Column(Boolean, default=False)
    tipo_error = Column(String(100))
    mensaje_error = Column(Text)
    
    # Campos opcionales
    origen_canal = Column(String(50))
    modelo_llm_usado = Column(String(100))
    
    # Relaciones
    usuario = relationship("Usuario")
    prompt = relationship("Prompt")

class FeedbackRespuesta(Base):
    __tablename__ = "feedback_respuesta"
    
    id_feedback = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("consultas.id_consulta"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    # En SQLite no hay ENUM, así que usamos String
    utilidad_respuesta = Column(String(10))
    comentario = Column(Text)
    fecha = Column(DateTime, default=datetime.now)
    
    # Relaciones
    consulta = relationship("Consulta")
    usuario = relationship("Usuario")

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
                    conn.execute("SET FOREIGN_KEY_CHECKS=0")
                    conn.commit()
                    print("Verificación de claves foráneas desactivada temporalmente.")
            except Exception as e:
                print(f"Aviso: {e}")
        
        # Eliminar tablas si existen en orden inverso a las dependencias
        print("\nEliminando tablas existentes para recrearlas...")
        for tabla in reversed([FeedbackRespuesta, Consulta, Usuario, Prompt, LogBatchBDV, LogArranqueApp]):
            tabla_nombre = tabla.__tablename__
            try:
                tabla.__table__.drop(engine, checkfirst=True)
                print(f"Tabla '{tabla_nombre}' eliminada si existía.")
            except Exception as e:
                print(f"Nota al eliminar '{tabla_nombre}': {e}")
        
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
                    conn.execute("SET FOREIGN_KEY_CHECKS=1")
                    conn.commit()
                    print("Verificación de claves foráneas reactivada.")
            except Exception as e:
                print(f"Aviso: {e}")
        
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