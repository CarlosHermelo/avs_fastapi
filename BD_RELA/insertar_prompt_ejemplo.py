#!/usr/bin/env python
# BD_RELA/insertar_prompt_ejemplo.py

import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from create_tables import Prompt, get_engine

def insertar_prompt_ejemplo():
    """
    Inserta un prompt de ejemplo en la base de datos para pruebas
    """
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        print(f"\n{'='*80}")
        print(f"INSERCIÓN DE PROMPT DE EJEMPLO - Base de datos: {engine.name.upper()}")
        print(f"{'='*80}")

        # Leer contenido del archivo prompt_fallback.txt
        prompt_file_path = os.path.join(project_root, 'prompt_fallback.txt')
        
        if not os.path.exists(prompt_file_path):
            print(f"Error: El archivo prompt_fallback.txt no se encuentra en {prompt_file_path}")
            return

        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()

        if not contenido:
            print("El archivo prompt_fallback.txt está vacío.")
            return

        # Desactivar cualquier prompt activo anterior
        prompts_activos = session.query(Prompt).filter(Prompt.activo == True).all()
        if prompts_activos:
            print(f"Desactivando {len(prompts_activos)} prompt(s) activo(s) anterior(es)...")
            for prompt in prompts_activos:
                prompt.activo = False
                print(f"  - Desactivado: ID {prompt.id_prompt} - {prompt.nombre_prompt}")

        # Insertar nuevo prompt como activo
        nuevo_prompt = Prompt(
            nombre_prompt="Prompt SIMAP Dinámico",
            contenido_prompt=contenido,
            version=datetime.now().strftime("%Y%m%d%H%M%S"),
            activo=True,
            fecha_creacion=datetime.now()
        )
        
        session.add(nuevo_prompt)
        session.commit()

        print(f"\n✓ Nuevo prompt insertado exitosamente:")
        print(f"  - ID: {nuevo_prompt.id_prompt}")
        print(f"  - Nombre: {nuevo_prompt.nombre_prompt}")
        print(f"  - Versión: {nuevo_prompt.version}")
        print(f"  - Estado: ACTIVO")
        print(f"  - Longitud del contenido: {len(contenido)} caracteres")
        print(f"  - Fecha de creación: {nuevo_prompt.fecha_creacion}")

        # Verificar que el prompt se insertó correctamente
        prompt_verificacion = session.query(Prompt).filter(Prompt.activo == True).first()
        if prompt_verificacion and prompt_verificacion.id_prompt == nuevo_prompt.id_prompt:
            print(f"\n✓ Verificación exitosa: El prompt está activo en la base de datos")
        else:
            print(f"\n✗ Error en la verificación: El prompt no se encuentra activo")

        session.close()

    except Exception as e:
        print(f"Error al insertar el prompt de ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    insertar_prompt_ejemplo() 