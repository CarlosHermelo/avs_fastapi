#!/usr/bin/env python
# BD_RELA/crear_tabla_prompts.py

import sys
import os
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Agregar el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from create_tables import get_engine  # Usa tu función actual de conexión

Base = declarative_base()

class Prompt(Base):
    __tablename__ = 'prompts'

    id_prompt = Column(Integer, primary_key=True, autoincrement=True)
    nombre_prompt = Column(String(100), nullable=False)
    contenido_prompt = Column(Text, nullable=False)
    version = Column(String(50), nullable=True)
    activo = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

def crear_tabla_prompts():
    try:
        engine = get_engine()
        db_type = engine.name.upper()
        inspector = inspect(engine)

        print(f"\n{'='*80}")
        print(f"VERIFICACIÓN DE TABLA 'prompts' - Base de datos: {db_type}")
        print(f"{'='*80}")

        if 'prompts' in inspector.get_table_names():
            print("La tabla 'prompts' ya existe. No se realizaron cambios.")
            return

        Base.metadata.create_all(engine)
        print("Tabla 'prompts' creada correctamente.")

    except Exception as e:
        print(f"Error al crear la tabla 'prompts': {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_tabla_prompts()
