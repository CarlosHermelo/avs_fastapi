#!/usr/bin/env python
# BD_RELA/temp_config.py
import os
import sys

# Establecer manualmente la variable DB_TYPE
os.environ["DB_TYPE"] = "mysql"

# Importar y ejecutar la función get_engine para probar la conexión
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from create_tables import get_engine

# Probar la conexión
print("\nProbando conexión a la base de datos...")
engine = get_engine()

print("\nScript completado. Por favor, asegúrese de añadir la variable DB_TYPE=mysql al archivo .env") 