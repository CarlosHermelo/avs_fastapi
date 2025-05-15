#!/usr/bin/env python
# BD_RELA/diag_mysql.py
import os
import sys
from sqlalchemy import create_engine, text

# Obtener las credenciales del entorno
DB_HOST = os.getenv("BD_SERVER", "mysqldesa.pami.ar")
DB_PORT = os.getenv("BD_PORT", "3306")
DB_NAME = os.getenv("BD_NAME", "avsp")
DB_USER = os.getenv("BD_USER", "avsp")
DB_PASS = os.getenv("BD_PASSWD", "Des2025avsp")

print(f"Diagnosticando conexión a MySQL...")
print(f"Host: {DB_HOST}")
print(f"Puerto: {DB_PORT}")
print(f"Base de datos: {DB_NAME}")
print(f"Usuario: {DB_USER}")
print(f"Contraseña: {'*' * len(DB_PASS)}")

# Construir URL de conexión para MySQL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
print(f"URL de conexión: {DATABASE_URL}")

try:
    # Crear motor para MySQL con log de debugging
    print("\nCreando motor de base de datos...")
    engine = create_engine(
        DATABASE_URL,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=True,  # Activar debugging
        connect_args={
            "connect_timeout": 60,
            "sql_mode": "NO_AUTO_VALUE_ON_ZERO"
        }
    )
    
    # Verificar la conexión
    print("\nIntentando conexión...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Resultado: {result.fetchone()}")
        print("¡Conexión a MySQL exitosa!")
    
except Exception as e:
    print(f"\nError al conectar con MySQL:")
    print(f"Tipo de error: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\nPosibles soluciones:")
    print("1. Verificar credenciales en el archivo .env")
    print("2. Verificar que el servidor MySQL esté activo y accesible")
    print("3. Verificar que la base de datos exista")
    print("4. Verificar que el usuario tenga permisos para acceder a la base de datos")
    
print("\nDiagnóstico completado.") 