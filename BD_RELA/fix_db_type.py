#!/usr/bin/env python
# BD_RELA/fix_db_type.py
import os
import sys
import re

def add_db_type_to_env():
    """Añade la variable DB_TYPE=mysql al archivo .env si no existe"""
    # Ruta al archivo .env en el directorio raíz
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    if not os.path.exists(env_path):
        print(f"Error: No se encontró el archivo .env en {env_path}")
        return False
    
    # Leer el contenido actual
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Verificar si ya existe DB_TYPE
    if re.search(r'^\s*DB_TYPE\s*=', content, re.MULTILINE):
        print("La variable DB_TYPE ya existe en el archivo .env")
        # Actualizar el valor si es necesario
        new_content = re.sub(r'^\s*DB_TYPE\s*=.*$', 'DB_TYPE=mysql', content, flags=re.MULTILINE)
        if new_content != content:
            print("Actualizando el valor a 'mysql'...")
            try:
                with open(env_path, 'w') as f:
                    f.write(new_content)
                print("¡Archivo .env actualizado correctamente!")
            except Exception as e:
                print(f"Error al escribir el archivo: {str(e)}")
                return False
        return True
    
    # Añadir la variable al final del archivo
    new_line = "\n# Tipo de base de datos (mysql/sqlite)\nDB_TYPE=mysql\n"
    
    try:
        with open(env_path, 'a') as f:
            f.write(new_line)
        print(f"¡Variable DB_TYPE=mysql añadida al archivo .env!")
        return True
    except Exception as e:
        print(f"Error al escribir el archivo: {str(e)}")
        return False

def fix_execute_query():
    """Corrige la ejecución de la consulta en create_tables.py"""
    create_tables_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'create_tables.py')
    
    if not os.path.exists(create_tables_path):
        print(f"Error: No se encontró el archivo create_tables.py en {create_tables_path}")
        return False
    
    # Leer el contenido actual
    with open(create_tables_path, 'r') as f:
        content = f.read()
    
    # Buscar y reemplazar la línea problemática
    pattern = r'(conn\.execute\()"(SELECT 1)"(\))'
    replacement = r'\1text("SELECT 1")\3'
    
    if 'from sqlalchemy import' in content and 'text' not in content:
        # Necesitamos añadir la importación de text
        content = content.replace(
            'from sqlalchemy import create_engine,',
            'from sqlalchemy import create_engine, text,'
        )
        content = content.replace(
            'from sqlalchemy import create_engine',
            'from sqlalchemy import create_engine, text'
        )
    
    # Reemplazar la ejecución de la consulta
    new_content = re.sub(pattern, replacement, content)
    
    if new_content == content:
        print("No fue necesario corregir la ejecución de la consulta")
        return True
    
    try:
        with open(create_tables_path, 'w') as f:
            f.write(new_content)
        print("¡Archivo create_tables.py corregido correctamente!")
        return True
    except Exception as e:
        print(f"Error al escribir el archivo: {str(e)}")
        return False

if __name__ == "__main__":
    print("Iniciando la corrección...")
    
    env_result = add_db_type_to_env()
    query_result = fix_execute_query()
    
    if env_result and query_result:
        print("\n¡Correcciones completadas con éxito!")
        print("Ahora el sistema debería usar MySQL en lugar de SQLite.")
        print("\nPara probar, ejecute: python create_tables.py")
    else:
        print("\nNo se pudieron completar todas las correcciones.")
        print("Por favor, añada manualmente la variable DB_TYPE=mysql al archivo .env")
        print("y corrija la ejecución de la consulta en create_tables.py") 