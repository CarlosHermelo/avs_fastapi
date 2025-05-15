#!/usr/bin/env python
# BD_RELA/drop_all_tables.py
import sys
import os
import traceback
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Importar desde el mismo directorio
from create_tables import get_engine

def eliminar_todas_las_tablas():
    """Elimina todas las tablas ignorando las restricciones de clave foránea."""
    try:
        # Obtener motor de base de datos
        engine = get_engine()
        
        # Tablas a eliminar en orden
        tablas = [
            "feedback_respuesta",
            "consultas",
            "prompts",
            "usuarios",
            "log_batch_bdv",
            "log_arranque_app"
        ]
        
        # Conectar a la base de datos
        with engine.connect() as conn:
            # Desactivar verificación de claves foráneas (MySQL)
            try:
                print("Desactivando verificación de claves foráneas...")
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                conn.commit()
                print("Verificación de claves foráneas desactivada.")
            except Exception as e:
                print(f"Aviso: {e}")
                print("Continuando sin desactivar claves foráneas...")
            
            # Eliminar cada tabla
            print("\nEliminando tablas forzadamente...")
            for tabla in tablas:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
                    conn.commit()
                    print(f"Tabla '{tabla}' eliminada con éxito.")
                except Exception as e:
                    print(f"Error al eliminar tabla '{tabla}': {e}")
            
            # Reactivar verificación de claves foráneas (MySQL)
            try:
                print("\nReactivando verificación de claves foráneas...")
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                conn.commit()
                print("Verificación de claves foráneas reactivada.")
            except Exception as e:
                print(f"Aviso: {e}")
        
        print("\nProceso de eliminación de tablas finalizado.")
        
    except Exception as e:
        print(f"Error general: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Iniciando proceso de eliminación forzada de todas las tablas...")
    eliminar_todas_las_tablas()
    print("\nPara crear nuevamente las tablas, ejecute: python create_tables.py") 