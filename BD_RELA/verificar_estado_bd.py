#!/usr/bin/env python3
# BD_RELA/verificar_estado_bd.py
"""
Script para verificar el estado actual de las bases de datos.
Muestra información sobre foreign keys y estructura de tablas.

Uso:
    python BD_RELA/verificar_estado_bd.py
"""

import sys
import os
from dotenv import load_dotenv
import sqlite3
import pymysql
import traceback

# Cargar variables de entorno
load_dotenv()

def verificar_sqlite():
    """Verifica el estado de la base SQLite."""
    print("\n🔍 VERIFICANDO SQLite...")
    print("-" * 40)
    
    sqlite_path = os.getenv("SQLITE_PATH", "BD_RELA/local_database.db")
    
    if not os.path.exists(sqlite_path):
        print(f"❌ Archivo SQLite no encontrado: {sqlite_path}")
        return False
    
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print(f"✅ Conectado a SQLite: {sqlite_path}")
        
        # Listar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tablas = cursor.fetchall()
        print(f"📋 Tablas encontradas: {len(tablas)}")
        for tabla in tablas:
            print(f"   - {tabla[0]}")
        
        # Verificar estructura de consultas
        if any(t[0] == 'consultas' for t in tablas):
            cursor.execute("PRAGMA table_info(consultas)")
            columnas = cursor.fetchall()
            print(f"\n📊 Estructura tabla 'consultas':")
            for col in columnas:
                print(f"   {col['name']}: {col['type']} {'NOT NULL' if col['notnull'] else 'NULL'} {'PK' if col['pk'] else ''}")
            
            # Verificar foreign keys en SQLite
            cursor.execute("PRAGMA foreign_key_list(consultas)")
            fks = cursor.fetchall()
            if fks:
                print(f"🔗 Foreign Keys en 'consultas': {len(fks)}")
                for fk in fks:
                    print(f"   {fk['from']} -> {fk['table']}.{fk['to']}")
            else:
                print("✅ No hay foreign keys en 'consultas' (correcto para SQLite)")
        
        # Contar registros
        if any(t[0] == 'consultas' for t in tablas):
            cursor.execute("SELECT COUNT(*) FROM consultas")
            count = cursor.fetchone()[0]
            print(f"📈 Registros en 'consultas': {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando SQLite: {e}")
        return False

def verificar_mysql():
    """Verifica el estado de la base MySQL."""
    print("\n🔍 VERIFICANDO MySQL...")
    print("-" * 40)
    
    DB_HOST = os.getenv("BD_SERVER", "localhost")
    DB_PORT = int(os.getenv("BD_PORT", 3306))
    DB_NAME = os.getenv("BD_NAME", "avsp")
    DB_USER = os.getenv("BD_USER", "root")
    DB_PASS = os.getenv("BD_PASSWD", "")
    
    try:
        conexion = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        
        print(f"✅ Conectado a MySQL: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        with conexion.cursor() as cursor:
            # Listar tablas
            cursor.execute("SHOW TABLES")
            tablas = cursor.fetchall()
            print(f"📋 Tablas encontradas: {len(tablas)}")
            for tabla in tablas:
                tabla_nombre = list(tabla.values())[0]
                print(f"   - {tabla_nombre}")
            
            # Verificar estructura de consultas
            if any('consultas' in list(t.values())[0] for t in tablas):
                cursor.execute("DESCRIBE consultas")
                columnas = cursor.fetchall()
                print(f"\n📊 Estructura tabla 'consultas':")
                for col in columnas:
                    print(f"   {col['Field']}: {col['Type']} {col['Null']} {col['Key']} {col['Extra']}")
                
                # Verificar foreign keys
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME,
                        CONSTRAINT_NAME
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'consultas'
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (DB_NAME,))
                
                fks = cursor.fetchall()
                if fks:
                    print(f"🔗 Foreign Keys en 'consultas': {len(fks)}")
                    for fk in fks:
                        print(f"   {fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']} ({fk['CONSTRAINT_NAME']})")
                else:
                    print("✅ No hay foreign keys en 'consultas' (migración exitosa)")
            
            # Contar registros
            if any('consultas' in list(t.values())[0] for t in tablas):
                cursor.execute("SELECT COUNT(*) as count FROM consultas")
                result = cursor.fetchone()
                print(f"📈 Registros en 'consultas': {result['count']}")
        
        conexion.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando MySQL: {e}")
        print("   (Es normal si MySQL no está configurado o disponible)")
        return False

def main():
    """Función principal del script de verificación."""
    print("🔍 VERIFICADOR DE ESTADO DE BASES DE DATOS")
    print("=" * 50)
    
    db_type = os.getenv("DB_TYPE", "sqlite")
    print(f"🎯 DB_TYPE configurado: {db_type}")
    
    # Verificar SQLite siempre
    sqlite_ok = verificar_sqlite()
    
    # Verificar MySQL si está configurado
    mysql_ok = False
    if db_type.lower() == "mysql":
        mysql_ok = verificar_mysql()
    else:
        print(f"\n⏭️  Saltando verificación de MySQL (DB_TYPE={db_type})")
    
    # Resumen
    print("\n📋 RESUMEN:")
    print("-" * 20)
    print(f"SQLite: {'✅ OK' if sqlite_ok else '❌ ERROR'}")
    print(f"MySQL:  {'✅ OK' if mysql_ok else '❌ ERROR/NO CONFIGURADO'}")
    
    if db_type.lower() == "sqlite" and sqlite_ok:
        print("\n🎉 Configuración actual es compatible con la aplicación.")
    elif db_type.lower() == "mysql" and mysql_ok:
        print("\n🎉 Configuración MySQL verificada.")
    else:
        print("\n⚠️  Revisar configuración o ejecutar migración si es necesario.")
    
    return sqlite_ok or mysql_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 