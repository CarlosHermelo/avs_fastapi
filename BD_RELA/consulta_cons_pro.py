import sys
import os
from sqlalchemy import text
from tabulate import tabulate

# Añadir el directorio raíz del proyecto a sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar la función para obtener el engine
from create_tables import get_engine

def ejecutar_select():
    try:
        engine = get_engine()
        query = text("""
            SELECT 
                c.pregunta_usuario AS pregunta,
                p.id_prompt,
                p.nombre_prompt,
                p.contenido_prompt,
                p.version,
                p.activo,
                p.fecha_creacion,
                c.id_prompt_usado AS pro_us
            FROM 
                consultas c
            JOIN 
                prompts p ON c.id_prompt_usado = p.id_prompt
            LIMIT 50
        """)

        with engine.connect() as conn:
            resultado = conn.execute(query)
            filas = resultado.fetchall()

            if filas:
                print(tabulate(filas, headers=resultado.keys(), tablefmt="grid"))
            else:
                print("No se encontraron registros.")

    except Exception as e:
        print(f"Error al ejecutar el SELECT: {e}")

if __name__ == "__main__":
    ejecutar_select()
