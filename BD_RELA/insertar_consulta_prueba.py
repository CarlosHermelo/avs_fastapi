#!/usr/bin/env python
# BD_RELA/insertar_consulta_prueba.py
import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Importar módulos necesarios desde el mismo directorio
from create_tables import Consulta, get_engine

def insertar_consulta_prueba():
    """Inserta una consulta de prueba en la base de datos."""
    try:
        # Obtener motor y crear sesión
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Crear respuesta para la consulta
        respuesta = "Para inscribir a un alumno en el sistema necesitará: 1) DNI del estudiante, 2) Certificado de domicilio, 3) Formulario de inscripción completo, 4) Certificado de estudios previos."
        
        # Verificar longitud de respuesta (menos de 150 caracteres se considera error)
        es_error = len(respuesta) < 150
        
        # Crear objeto consulta de prueba
        consulta = Consulta(
            timestamp=datetime.now(),
            id_usuario=321,
            ugel_origen="Formosa",
            pregunta_usuario="¿Cuáles son los requisitos para inscribir a un alumno en el sistema?",
            respuesta_asistente=respuesta,
            respuesta_es_vacia=False,
            respuesta_util="sin feedback",
            id_prompt_usado=1,  # Debe existir en la tabla prompts
            tokens_input=150,
            tokens_output=200,
            tiempo_respuesta_ms=1250,
            error_detectado=es_error,
            tipo_error="Respuesta demasiado corta" if es_error else None,
            mensaje_error=f"La respuesta tiene {len(respuesta)} caracteres (mínimo 150)" if es_error else None,
            origen_canal="web",
            modelo_llm_usado="GPT-4"
        )
        
        # Añadir y confirmar
        session.add(consulta)
        session.commit()
        
        print(f"Consulta de prueba insertada correctamente con ID: {consulta.id_consulta}")
        
        # Cerrar sesión
        session.close()
        
    except Exception as e:
        print(f"Error al insertar consulta de prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Insertando consulta de prueba...")
    insertar_consulta_prueba() 