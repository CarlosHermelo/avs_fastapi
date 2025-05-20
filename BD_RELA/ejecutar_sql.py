#!/usr/bin/env python
# BD_RELA/ejecutar_select_interactivo.py

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy import inspect
from create_tables import get_engine
from tabulate import tabulate

def ejecutar_select_interactivo():
    try:
        # Agregar raíz del proyecto a sys.path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Conectarse a la base de datos
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        # Verificar si la base tiene tablas
        inspector = inspect(engine)
        tablas = inspector.get_table_names()
        if not tablas:
            print("No hay tablas en la base de datos.")
            return

        # Mostrar mensaje y esperar entrada del usuario
        print("Ingrese una consulta SELECT completa (ej: SELECT * FROM consultas LIMIT 5):")
        sql_input = input("SQL> ").strip()

        # Validar que empiece con SELECT
        if not sql_input.lower().startswith("select"):
            print("Error: solo se permiten consultas que comiencen con SELECT.")
            return

        # Ejecutar la consulta
        result = session.execute(text(sql_input))
        rows = result.fetchall()

        if not rows:
            print("La consulta no devolvió resultados.")
            return

        # Obtener nombres de columnas
        columnas = result.keys()
        print("\nResultado de la consulta:\n")
        print(tabulate(rows, headers=columnas, tablefmt="grid"))

        session.close()

    except Exception as e:
        print(f"Error al ejecutar la consulta: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ejecutar_select_interactivo()
