#!/usr/bin/env python
# BD_RELA/insertar_prompt.py

import sys
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from create_tables import Prompt, get_engine

def insertar_prompt_desde_txt():
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        print(f"\n{'='*80}")
        print(f"INSERCIÓN DE NUEVO PROMPT - Base de datos: {engine.name.upper()}")
        print(f"{'='*80}")

        # Leer contenido del archivo prompt.txt
        ruta_prompt = os.path.join(os.path.dirname(__file__), 'prompt.txt')
        if not os.path.exists(ruta_prompt):
            print(f"Error: El archivo prompt.txt no se encuentra en {ruta_prompt}")
            return

        with open(ruta_prompt, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()

        if not contenido:
            print("El archivo prompt.txt está vacío.")
            return

        # Desactivar cualquier prompt activo anterior
        session.query(Prompt).filter(Prompt.activo == True).update({"activo": False})

        # Insertar nuevo prompt como activo
        nuevo_prompt = Prompt(
            nombre_prompt="system",
            contenido_prompt=contenido,
            version=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            activo=True
        )
        session.add(nuevo_prompt)
        session.commit()

        print(f"Nuevo prompt insertado con ID: {nuevo_prompt.id_prompt}")
        print(f"Nombre: {nuevo_prompt.nombre_prompt}")
        print("Estado: ACTIVO")

        session.close()

    except Exception as e:
        print(f"Error al insertar el nuevo prompt: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    insertar_prompt_desde_txt()
