# app/services/db_service.py
import sys
import os
import traceback
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json # Importar json para serializar el diccionario de datos

# Importamos la clase Consulta de BD_RELA
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from BD_RELA.create_tables import Consulta, get_engine
from app.core.logging_config import get_logger, log_message

# Configurar logger
logger = get_logger()

def persistir_consulta(
    pregunta_usuario,
    respuesta_asistente,
    id_usuario,
    ugel_origen,
    tokens_input,
    tokens_output,
    tiempo_respuesta_ms,
    error_detectado=False,
    tipo_error=None,
    mensaje_error=None,
    modelo_llm_usado=None
):
    """
    Guarda un registro de consulta en la base de datos relacional.
    
    IMPORTANTE: Los parámetros tokens_input y tokens_output deben ser valores
    ya calculados previamente usando la función contar_tokens(). No se deben
    calcular nuevamente aquí para evitar inconsistencias entre logs y BD.
    
    Args:
        pregunta_usuario (str): Texto de la pregunta del usuario
        respuesta_asistente (str): Texto de la respuesta generada
        id_usuario (int): ID del usuario que realiza la consulta
        ugel_origen (str): UGL de origen del usuario
        tokens_input (int): Número de tokens usados en el prompt (ya calculado)
        tokens_output (int): Número de tokens generados en la respuesta (ya calculado)
        tiempo_respuesta_ms (int): Tiempo en ms para generar la respuesta
        error_detectado (bool): Si ocurrió un error técnico
        tipo_error (str): Tipo de error si hubo alguno
        mensaje_error (str): Mensaje de error detallado
        modelo_llm_usado (str): Modelo LLM utilizado
    
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    # Preparar datos para el log antes de la inserción
    datos_a_insertar = {
        "timestamp": datetime.now().isoformat(), # Usar isoformat para el log
        "id_usuario": id_usuario,
        "ugel_origen": ugel_origen or "Formosa",
        "pregunta_usuario": pregunta_usuario,
        "respuesta_asistente": respuesta_asistente,
        "respuesta_es_vacia": len(respuesta_asistente or "") < 150,
        "respuesta_util": None,
        "id_prompt_usado": 1,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tiempo_respuesta_ms": tiempo_respuesta_ms,
        "error_detectado": error_detectado,
        "tipo_error": tipo_error,
        "mensaje_error": mensaje_error,
        "origen_canal": None,
        "modelo_llm_usado": modelo_llm_usado
    }

    try:
        # Obtener motor y sesión
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verificar si el id_usuario existe
        usuario_existe = False
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                resultado = conn.execute(text(f"SELECT COUNT(*) FROM usuarios WHERE id_usuario = {datos_a_insertar['id_usuario']}"))
                count = resultado.scalar()
                usuario_existe = count > 0
            
            if not usuario_existe:
                logger.warning(f"El id_usuario={datos_a_insertar['id_usuario']} no existe. Usando id_usuario=321 por defecto.")
                datos_a_insertar['id_usuario'] = 321
        except Exception as e:
            logger.warning(f"Error al verificar si el usuario existe: {e}. Usando id_usuario=321 por defecto.")
            datos_a_insertar['id_usuario'] = 321
        
        # Ajustar tokens y tiempo_respuesta_ms (mantenemos lógica existente)
        try:
            datos_a_insertar['tokens_input'] = int(datos_a_insertar['tokens_input']) if datos_a_insertar['tokens_input'] is not None else 0
            datos_a_insertar['tokens_output'] = int(datos_a_insertar['tokens_output']) if datos_a_insertar['tokens_output'] is not None else 0
            datos_a_insertar['tiempo_respuesta_ms'] = int(datos_a_insertar['tiempo_respuesta_ms']) if datos_a_insertar['tiempo_respuesta_ms'] is not None else 0
            
            if datos_a_insertar['tokens_input'] < 0:
                logger.warning(f"Valor de tokens_input negativo ({datos_a_insertar['tokens_input']}). Usando 0.")
                datos_a_insertar['tokens_input'] = 0
            if datos_a_insertar['tokens_output'] < 0:
                logger.warning(f"Valor de tokens_output negativo ({datos_a_insertar['tokens_output']}). Usando 0.")
                datos_a_insertar['tokens_output'] = 0
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir valores: input={datos_a_insertar['tokens_input']}, output={datos_a_insertar['tokens_output']}: {str(e)}")
            datos_a_insertar['tokens_input'] = 0
            datos_a_insertar['tokens_output'] = 0
        
        # Log de los datos que se intentarán insertar
        # Usamos json.dumps para formatear el diccionario de forma legible en el log
        logger.info(f"Intentando insertar en tabla 'consultas'. Datos: {json.dumps(datos_a_insertar, indent=2, ensure_ascii=False)}")
        
        # Crear registro de consulta
        consulta = Consulta(
            timestamp=datetime.fromisoformat(datos_a_insertar["timestamp"]), # Convertir de nuevo a datetime
            id_usuario=datos_a_insertar["id_usuario"],
            ugel_origen=datos_a_insertar["ugel_origen"],
            pregunta_usuario=datos_a_insertar["pregunta_usuario"],
            respuesta_asistente=datos_a_insertar["respuesta_asistente"],
            respuesta_es_vacia=datos_a_insertar["respuesta_es_vacia"],
            respuesta_util=datos_a_insertar["respuesta_util"],
            id_prompt_usado=datos_a_insertar["id_prompt_usado"],
            tokens_input=datos_a_insertar["tokens_input"],
            tokens_output=datos_a_insertar["tokens_output"],
            tiempo_respuesta_ms=datos_a_insertar["tiempo_respuesta_ms"],
            error_detectado=datos_a_insertar["error_detectado"],
            tipo_error=datos_a_insertar["tipo_error"],
            mensaje_error=datos_a_insertar["mensaje_error"],
            origen_canal=datos_a_insertar["origen_canal"],
            modelo_llm_usado=datos_a_insertar["modelo_llm_usado"]
        )
        
        session.add(consulta)
        session.commit()
        
        logger.info(f"INSERT en tabla 'consultas' exitoso. ID asignado: {consulta.id_consulta}. Status: ÉXITO.")
        logger.info(f"Tokens guardados para ID {consulta.id_consulta}: input={consulta.tokens_input}, output={consulta.tokens_output}")
        
        session.close()
        return consulta.id_consulta
        
    except SQLAlchemyError as e:
        logger.error(f"Error de SQLAlchemy al intentar insertar en tabla 'consultas'. Status: FALLIDO.")
        logger.error(f"Datos que se intentaron insertar: {json.dumps(datos_a_insertar, indent=2, ensure_ascii=False)}")
        logger.error(f"Detalles del error: {str(e)}")
        logger.error(traceback.format_exc())
        return None
        
    except Exception as e:
        logger.error(f"Error general al intentar insertar en tabla 'consultas'. Status: FALLIDO.")
        logger.error(f"Datos que se intentaron insertar: {json.dumps(datos_a_insertar, indent=2, ensure_ascii=False)}")
        logger.error(f"Detalles del error: {str(e)}")
        logger.error(traceback.format_exc())
        return None 