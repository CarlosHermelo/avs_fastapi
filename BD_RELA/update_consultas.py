#!/usr/bin/env python
# BD_RELA/actualizar_ugel_varios.py

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from create_tables import get_engine, Consulta

def actualizar_ugel_varios():
    try:
        # Configurar acceso al proyecto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Conexión a base de datos
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        # Verificar si la tabla existe
        inspector = inspect(engine)
        if "consultas" not in inspector.get_table_names():
            print("La tabla 'consultas' no existe.")
            return

        # Obtener los primeros 10 registros ordenados por ID
        registros = session.query(Consulta).order_by(Consulta.id_consulta.asc()).limit(10).all()

        if len(registros) < 10:
            print(f"Advertencia: solo se encontraron {len(registros)} registros.")
        
        # Asignar valores por grupo
        for i, consulta in enumerate(registros):
            if i < 4:
                nuevo_ugel = "Usuahia"
            elif i < 7:
                nuevo_ugel = "Neuquen"
            elif i < 9:
                nuevo_ugel = "Entre Rios"
            else:
                nuevo_ugel = "Cordoba"

            print(f"ID {consulta.id_consulta}: ugel_origen -> {nuevo_ugel}")
            consulta.ugel_origen = nuevo_ugel

        session.commit()
        print("Actualización completada para 10 registros.")
        session.close()

    except Exception as e:
        print(f"Error al actualizar ugel_origen: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    actualizar_ugel_varios()
