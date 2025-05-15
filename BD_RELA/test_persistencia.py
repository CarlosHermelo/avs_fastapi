#!/usr/bin/env python
# BD_RELA/test_persistencia.py
import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Importar clases y funciones necesarias
from create_tables import Consulta, get_engine

def test_guardar_consulta():
    """
    Guarda una consulta de prueba en la base de datos
    para verificar que la persistencia funciona correctamente.
    """
    # Obtener engine y crear sesión
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Crear una consulta de prueba
        consulta = Consulta(
            timestamp=datetime.now(),
            id_usuario=321,  # Usuario predeterminado del sistema
            ugel_origen="Formosa",  # Valor fijo según requisitos
            pregunta_usuario="Consulta de prueba usando el usuario predeterminado (ID 321)",
            respuesta_asistente="Esta es una respuesta de prueba para verificar que la persistencia con el usuario ID 321 funciona correctamente.",
            respuesta_es_vacia=None,  # Más de 150 caracteres
            respuesta_util=None,
            id_prompt_usado=1,
            tokens_input=100,
            tokens_output=50,
            tiempo_respuesta_ms=500,
            error_detectado=False,
            tipo_error=None,
            mensaje_error=None,
            origen_canal=None,
            modelo_llm_usado="gpt-4"
        )
        
        # Guardar en la base de datos
        session.add(consulta)
        session.commit()
        
        print(f"Consulta de prueba guardada exitosamente con ID: {consulta.id_consulta}")
        print(f"Timestamp: {consulta.timestamp}")
        print(f"ID Usuario: {consulta.id_usuario}")
        print(f"UGL Origen: {consulta.ugel_origen}")
        
        # Cerrar sesión
        session.close()
        return True
        
    except Exception as e:
        print(f"Error al guardar la consulta de prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False

if __name__ == "__main__":
    print("Ejecutando prueba de persistencia con usuario ID 321...")
    test_guardar_consulta()
    print("\nConsulta almacenada. Ejecute 'python listar_consultas_simple.py --respuestas' para verificar.") 