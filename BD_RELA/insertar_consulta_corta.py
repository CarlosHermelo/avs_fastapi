#!/usr/bin/env python
# BD_RELA/insertar_consulta_corta.py
import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Importar módulos necesarios desde el mismo directorio
from create_tables import Consulta, get_engine

def insertar_consulta_corta():
    """Inserta una consulta con respuesta corta (menos de 150 chars) que se marcará como error."""
    try:
        # Obtener motor y crear sesión
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Crear respuesta corta (menos de 150 caracteres)
        respuesta = "No tengo información sobre ese trámite específico."
        
        # Verificar longitud de respuesta
        es_respuesta_corta = len(respuesta) < 150
        
        # Crear objeto consulta 
        consulta = Consulta(
            timestamp=datetime.now(),
            id_usuario=1,  # ID que existe en la tabla usuarios (creado por create_tables.py --test)
            ugel_origen="Formosa",
            pregunta_usuario="¿Cómo se realiza el trámite para solicitar licencia por maternidad?",
            respuesta_asistente=respuesta,
            respuesta_es_vacia=es_respuesta_corta,  # Si la respuesta es corta (< 150 chars), se considera vacía
            respuesta_util="sin feedback",
            id_prompt_usado=1,  # Debe existir en la tabla prompts
            tokens_input=120,
            tokens_output=30,
            tiempo_respuesta_ms=980,
            error_detectado=es_respuesta_corta,
            tipo_error="Respuesta demasiado corta" if es_respuesta_corta else None,
            mensaje_error=f"La respuesta tiene {len(respuesta)} caracteres (mínimo 150)" if es_respuesta_corta else None,
            origen_canal="web",
            modelo_llm_usado="GPT-4"
        )
        
        # Añadir y confirmar
        session.add(consulta)
        session.commit()
        
        print(f"Consulta con respuesta corta insertada correctamente con ID: {consulta.id_consulta}")
        print(f"Longitud de respuesta: {len(respuesta)} caracteres")
        print(f"Marcada como error: {'Sí' if es_respuesta_corta else 'No'}")
        print(f"Respuesta vacía: {'Sí' if es_respuesta_corta else 'No'}")
        
        # Cerrar sesión
        session.close()
        
    except Exception as e:
        print(f"Error al insertar consulta: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Insertando consulta con respuesta corta...")
    insertar_consulta_corta()
    
    # Comentar la siguiente línea si solo desea insertar una consulta
    # insertar_otra_consulta_corta() 