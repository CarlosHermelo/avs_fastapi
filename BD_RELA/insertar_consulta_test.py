#!/usr/bin/env python
# BD_RELA/insertar_consulta_test.py
import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Importar módulos necesarios desde el mismo directorio
from create_tables import Consulta, get_engine, Usuario

def insertar_consulta_test():
    """
    Inserta una consulta de prueba con valores específicos de tokens
    """
    # Obtener motor y crear sesión
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si el usuario con ID 321 existe
        usuario = session.query(Usuario).filter_by(id_usuario=321).first()
        
        # Si no existe, crearlo
        if not usuario:
            print("Creando usuario con ID 321...")
            nuevo_usuario = Usuario(
                id_usuario=321,
                nombre="Usuario SIMAP",
                ugel_origen="Formosa"
            )
            session.add(nuevo_usuario)
            session.commit()
            print("Usuario creado exitosamente")
        
        # Crear consulta de prueba con valores específicos de tokens
        consulta = Consulta(
            timestamp=datetime.now(),
            id_usuario=321,  # ID de usuario fijo según instrucciones
            ugel_origen="Formosa",  # UGL fija según instrucciones
            pregunta_usuario="¿Cuál es el trámite para obtener una silla de ruedas?",
            respuesta_asistente="Para solicitar una silla de ruedas en PAMI, el afiliado debe presentar: receta electrónica del médico especialista con diagnóstico y prescripción detallada, formulario de solicitud de elementos de tecnología médica, fotocopia del DNI, y fotocopia de la credencial de afiliación. La solicitud se presenta en cualquier agencia o UGL de PAMI, y luego se evalúa a nivel central.",
            respuesta_es_vacia=False,
            respuesta_util=None,
            id_prompt_usado=1,
            tokens_input=1256,  # Valor específico para prueba
            tokens_output=785,  # Valor específico para prueba
            tiempo_respuesta_ms=3210,
            error_detectado=False,
            tipo_error=None,
            mensaje_error=None,
            origen_canal=None,
            modelo_llm_usado="gpt-4o-mini"
        )
        
        # Guardar en la base de datos
        session.add(consulta)
        session.commit()
        
        print(f"Consulta de prueba guardada exitosamente con ID: {consulta.id_consulta}")
        print(f"Tokens guardados: input={consulta.tokens_input}, output={consulta.tokens_output}")
        
    except Exception as e:
        print(f"Error al insertar consulta de prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
    
    finally:
        # Cerrar sesión
        session.close()

if __name__ == "__main__":
    insertar_consulta_test()
    print("\nAhora lista las consultas para verificar:")
    print("python listar_consultas.py --formato-tabla --limit 5") 