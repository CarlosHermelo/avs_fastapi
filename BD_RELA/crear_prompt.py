#!/usr/bin/env python
# BD_RELA/crear_prompt.py
import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Importar módulos necesarios desde el mismo directorio
from create_tables import Prompt, get_engine

def crear_prompt():
    """
    Crea un registro en la tabla prompts para habilitar la inserción en la tabla consultas
    """
    # Obtener motor y crear sesión
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si ya existen prompts
        prompt_existente = session.query(Prompt).filter_by(id_prompt=1).first()
        
        if prompt_existente:
            print(f"El prompt con ID 1, '{prompt_existente.nombre_prompt}', ya existe.")
            print(f"Activo: {prompt_existente.activo}")
            print(f"Fecha creación: {prompt_existente.fecha_creacion}")
            return
        
        # Crear un nuevo prompt
        nuevo_prompt = Prompt(
            id_prompt=1,
            nombre_prompt="Prompt SIMAP Default",
            contenido_prompt="Este es el prompt por defecto para el asistente SIMAP.",
            version=1,
            activo=True,
            fecha_creacion=datetime.now()
        )
        
        # Guardar en la base de datos
        session.add(nuevo_prompt)
        session.commit()
        
        print(f"Prompt creado exitosamente con ID: {nuevo_prompt.id_prompt}")
        
    except SQLAlchemyError as e:
        print(f"Error de SQLAlchemy al crear el prompt: {str(e)}")
        session.rollback()
        
    except Exception as e:
        print(f"Error general al crear el prompt: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
    
    finally:
        # Cerrar sesión
        session.close()

def consultar_prompts():
    """
    Muestra todos los prompts existentes
    """
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        prompts = session.query(Prompt).all()
        print(f"Prompts encontrados: {len(prompts)}")
        
        for p in prompts:
            print(f"ID: {p.id_prompt}, Nombre: {p.nombre_prompt}, Activo: {p.activo}, Fecha: {p.fecha_creacion}")
            
    except Exception as e:
        print(f"Error al consultar prompts: {str(e)}")
    
    finally:
        session.close()

if __name__ == "__main__":
    print("=== Creación de Prompt por defecto ===")
    crear_prompt()
    print("\n=== Prompts existentes ===")
    consultar_prompts() 