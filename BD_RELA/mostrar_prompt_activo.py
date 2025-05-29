#!/usr/bin/env python
# BD_RELA/mostrar_prompt_activo.py

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Agregar el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from create_tables import Prompt, get_engine

def mostrar_prompt_activo():
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        print(f"\n{'='*80}")
        print(f"MOSTRAR PROMPT ACTIVO")
        print(f"{'='*80}")

        # Buscar prompt con activo=True
        prompt_activo = session.execute(
            select(Prompt).where(Prompt.activo == True)
        ).scalars().first()

        if prompt_activo:
            print(f"ID: {prompt_activo.id_prompt}")
            print(f"Nombre: {prompt_activo.nombre_prompt}")
            print(f"Versión: {prompt_activo.version}")
            print(f"Fecha creación: {prompt_activo.fecha_creacion}")
            print(f"Contenido:\n{'-'*40}\n{prompt_activo.contenido_prompt}\n{'-'*40}")
        else:
            print("No hay ningún prompt activo en la tabla.")

        # DEBUG opcional: ver todos los prompts existentes
        print(f"\n{'='*80}")
        print("DEBUG: Contenido completo de la tabla 'prompts'")
        print(f"{'='*80}")
        prompts = session.execute(select(Prompt)).scalars().all()
        for p in prompts:
            print(f"ID: {p.id_prompt} | Nombre: {p.nombre_prompt} | Activo: {p.activo}")

        session.close()

    except Exception as e:
        print(f"Error al consultar el prompt activo: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    mostrar_prompt_activo()
