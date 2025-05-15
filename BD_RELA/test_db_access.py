#!/usr/bin/env python
# BD_RELA/test_db_access.py
import sys
import os
import traceback
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Ajustar el path para importar módulos necesarios
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from BD_RELA.create_tables import Consulta, Usuario, get_engine
from app.services.db_service import persistir_consulta
from app.core.logging_config import get_logger, log_message

# Configurar un logger simple para este script
import logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

def verificar_tablas_bd():
    """Verifica que todas las tablas necesarias existan en la base de datos"""
    logger.info("=== VERIFICANDO TABLAS EN LA BASE DE DATOS ===")
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tablas_existentes = inspector.get_table_names()
        
        logger.info(f"Tablas encontradas: {tablas_existentes}")
        
        # Verificar la existencia de tablas críticas
        if 'consultas' in tablas_existentes:
            logger.info("✅ La tabla 'consultas' existe")
        else:
            logger.error("❌ La tabla 'consultas' NO existe")
            
        if 'usuarios' in tablas_existentes:
            logger.info("✅ La tabla 'usuarios' existe")
        else:
            logger.error("❌ La tabla 'usuarios' NO existe")
            
        # Verificar estructura de la tabla consultas
        if 'consultas' in tablas_existentes:
            columnas = inspector.get_columns('consultas')
            logger.info(f"Columnas en tabla 'consultas': {[col['name'] for col in columnas]}")
            
            # Verificar columnas críticas
            columnas_requeridas = ['tokens_input', 'tokens_output', 'pregunta_usuario', 'respuesta_asistente']
            for col_req in columnas_requeridas:
                if col_req in [col['name'] for col in columnas]:
                    logger.info(f"✅ La columna '{col_req}' existe en 'consultas'")
                else:
                    logger.error(f"❌ La columna '{col_req}' NO existe en 'consultas'")
        
        return True
    except Exception as e:
        logger.error(f"Error al verificar tablas: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def verificar_usuario_id(id_usuario=321):
    """Verifica que el usuario con el ID especificado exista en la base de datos"""
    logger.info(f"=== VERIFICANDO USUARIO CON ID {id_usuario} ===")
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
        
        if usuario:
            logger.info(f"✅ Usuario con ID {id_usuario} encontrado: {usuario.nombre}, {usuario.ugel_origen}")
            return True
        else:
            logger.error(f"❌ Usuario con ID {id_usuario} NO encontrado")
            # Intentar crear el usuario
            logger.info(f"Intentando crear usuario con ID {id_usuario}...")
            try:
                nuevo_usuario = Usuario(
                    id_usuario=id_usuario,
                    nombre=f"Usuario SIMAP {id_usuario}",
                    ugel_origen="Formosa"
                )
                session.add(nuevo_usuario)
                session.commit()
                logger.info(f"✅ Usuario con ID {id_usuario} creado exitosamente")
                return True
            except Exception as create_err:
                logger.error(f"Error al crear usuario: {str(create_err)}")
                session.rollback()
                return False
    except Exception as e:
        logger.error(f"Error al verificar usuario: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        session.close()

def probar_persistir_consulta():
    """Prueba la función persistir_consulta directamente"""
    logger.info("=== PROBANDO FUNCIÓN persistir_consulta ===")
    
    try:
        # Datos de prueba
        pregunta = "¿Pregunta de prueba para diagnosticar el problema de persistencia?"
        respuesta = "Esta es una respuesta de prueba generada para diagnosticar por qué no se están guardando las consultas en la base de datos."
        id_usuario = 321
        ugel_origen = "Formosa"
        tokens_input = 100
        tokens_output = 200
        tiempo_respuesta_ms = 1500
        
        logger.info("Datos de la consulta de prueba:")
        logger.info(f"- Pregunta: {pregunta}")
        logger.info(f"- Respuesta: {respuesta[:50]}...")
        logger.info(f"- ID Usuario: {id_usuario}")
        logger.info(f"- UGL Origen: {ugel_origen}")
        logger.info(f"- Tokens input: {tokens_input}")
        logger.info(f"- Tokens output: {tokens_output}")
        logger.info(f"- Tiempo respuesta (ms): {tiempo_respuesta_ms}")
        
        # Llamar a la función persistir_consulta
        logger.info("Llamando a persistir_consulta()...")
        
        persistencia_ok = persistir_consulta(
            pregunta_usuario=pregunta,
            respuesta_asistente=respuesta,
            id_usuario=id_usuario,
            ugel_origen=ugel_origen,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tiempo_respuesta_ms=tiempo_respuesta_ms,
            error_detectado=False,
            modelo_llm_usado="gpt-4o-mini"
        )
        
        logger.info(f"Resultado de persistir_consulta: {persistencia_ok}")
        
        return persistencia_ok
    except Exception as e:
        logger.error(f"Error al probar persistir_consulta: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def probar_insercion_directa():
    """Prueba insertar una consulta directamente en la base de datos"""
    logger.info("=== PROBANDO INSERCIÓN DIRECTA EN LA BASE DE DATOS ===")
    
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Datos de prueba
        consulta = Consulta(
            timestamp=datetime.now(),
            id_usuario=321,
            ugel_origen="Formosa",
            pregunta_usuario="Pregunta de prueba con inserción directa",
            respuesta_asistente="Respuesta de prueba con inserción directa para diagnosticar el problema.",
            respuesta_es_vacia=False,
            respuesta_util=None,
            id_prompt_usado=1,
            tokens_input=150,
            tokens_output=250,
            tiempo_respuesta_ms=1200,
            error_detectado=False,
            tipo_error=None,
            mensaje_error=None,
            origen_canal=None,
            modelo_llm_usado="gpt-4o-mini"
        )
        
        logger.info("Insertando consulta directamente...")
        session.add(consulta)
        session.commit()
        
        logger.info(f"✅ Consulta insertada exitosamente con ID: {consulta.id_consulta}")
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error de SQLAlchemy al insertar consulta: {str(e)}")
        logger.error(traceback.format_exc())
        session.rollback()
        return False
    except Exception as e:
        logger.error(f"Error general al insertar consulta: {str(e)}")
        logger.error(traceback.format_exc())
        session.rollback()
        return False
    finally:
        session.close()

def verificar_permisos_bd():
    """Verifica los permisos de escritura en la base de datos"""
    logger.info("=== VERIFICANDO PERMISOS DE ESCRITURA EN LA BASE DE DATOS ===")
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Intentar ejecutar una consulta de escritura simple
            try:
                # Crear una tabla temporal
                conn.execute(text("CREATE TEMPORARY TABLE test_permisos (id INT)"))
                # Insertar un registro
                conn.execute(text("INSERT INTO test_permisos VALUES (1)"))
                # Verificar el registro
                result = conn.execute(text("SELECT * FROM test_permisos"))
                row = result.fetchone()
                
                if row and row[0] == 1:
                    logger.info("✅ Permisos de escritura verificados correctamente")
                    return True
                else:
                    logger.error("❌ Problema al verificar datos insertados")
                    return False
            except Exception as e:
                logger.error(f"❌ Error al probar permisos de escritura: {str(e)}")
                return False
    except Exception as e:
        logger.error(f"Error al verificar permisos: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def listar_ultimas_consultas(limit=5):
    """Lista las últimas consultas en la base de datos"""
    logger.info(f"=== LISTANDO ÚLTIMAS {limit} CONSULTAS ===")
    
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        consultas = session.query(Consulta).order_by(Consulta.id_consulta.desc()).limit(limit).all()
        
        if consultas:
            logger.info(f"Se encontraron {len(consultas)} consultas:")
            for i, consulta in enumerate(consultas):
                logger.info(f"Consulta #{i+1} (ID: {consulta.id_consulta}):")
                logger.info(f"  - Timestamp: {consulta.timestamp}")
                logger.info(f"  - Usuario: {consulta.id_usuario} / UGL: {consulta.ugel_origen}")
                logger.info(f"  - Pregunta: {consulta.pregunta_usuario[:50]}...")
                logger.info(f"  - Respuesta: {consulta.respuesta_asistente[:50]}...")
                logger.info(f"  - Tokens input/output: {consulta.tokens_input}/{consulta.tokens_output}")
                logger.info(f"  - Tiempo respuesta: {consulta.tiempo_respuesta_ms} ms")
                logger.info(f"  - Modelo: {consulta.modelo_llm_usado}")
                logger.info("  " + "-"*50)
        else:
            logger.warning("❌ No se encontraron consultas en la base de datos")
        
        return True
    except Exception as e:
        logger.error(f"Error al listar consultas: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        session.close()

def main():
    """Función principal que ejecuta todas las pruebas"""
    logger.info("="*80)
    logger.info("INICIO DE DIAGNÓSTICO DE BASE DE DATOS Y PERSISTENCIA")
    logger.info("="*80)
    
    # Paso 1: Verificar tablas
    if not verificar_tablas_bd():
        logger.error("Diagnóstico fallido en la verificación de tablas")
        return
    
    # Paso 2: Verificar usuario
    if not verificar_usuario_id():
        logger.error("Diagnóstico fallido en la verificación de usuario")
        return
    
    # Paso 3: Verificar permisos
    if not verificar_permisos_bd():
        logger.error("Diagnóstico fallido en la verificación de permisos")
        return
    
    # Paso 4: Listar consultas existentes
    listar_ultimas_consultas()
    
    # Paso 5: Probar inserción directa
    if not probar_insercion_directa():
        logger.error("Diagnóstico fallido en la prueba de inserción directa")
    else:
        logger.info("✅ Prueba de inserción directa exitosa")
    
    # Paso 6: Probar persistir_consulta
    if not probar_persistir_consulta():
        logger.error("Diagnóstico fallido en la prueba de persistir_consulta")
    else:
        logger.info("✅ Prueba de persistir_consulta exitosa")
    
    # Paso 7: Listar consultas nuevamente para verificar inserciones
    listar_ultimas_consultas()
    
    logger.info("="*80)
    logger.info("FIN DE DIAGNÓSTICO")
    logger.info("="*80)

if __name__ == "__main__":
    main() 