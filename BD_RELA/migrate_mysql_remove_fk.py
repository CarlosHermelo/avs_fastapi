#!/usr/bin/env python3
# BD_RELA/migrate_mysql_remove_fk.py
"""
Script para migrar base de datos MySQL eliminando foreign key constraints.
Esto permite que la aplicación funcione sin depender de la tabla usuarios.

Uso:
    python BD_RELA/migrate_mysql_remove_fk.py
"""

import sys
import os
from dotenv import load_dotenv
import pymysql
import traceback

# Cargar variables de entorno
load_dotenv()

# Configuración de MySQL
DB_HOST = os.getenv("BD_SERVER", "localhost")
DB_PORT = int(os.getenv("BD_PORT", 3306))
DB_NAME = os.getenv("BD_NAME", "avsp")
DB_USER = os.getenv("BD_USER", "root")
DB_PASS = os.getenv("BD_PASSWD", "")

def conectar_mysql():
    """Conecta a MySQL y retorna la conexión."""
    try:
        print(f"Conectando a MySQL: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        conexion = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=60
        )
        
        # Verificar conexión
        with conexion.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"✅ Conexión exitosa: {result}")
        
        return conexion
        
    except Exception as e:
        print(f"❌ Error al conectar a MySQL: {e}")
        return None

def listar_foreign_keys(conexion):
    """Lista todas las foreign keys existentes en las tablas del sistema."""
    try:
        with conexion.cursor() as cursor:
            query = """
                SELECT 
                    TABLE_NAME,
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE CONSTRAINT_SCHEMA = %s 
                AND REFERENCED_TABLE_NAME IS NOT NULL
                AND TABLE_NAME IN ('consultas', 'feedback_respuesta')
                ORDER BY TABLE_NAME, CONSTRAINT_NAME
            """
            cursor.execute(query, (DB_NAME,))
            foreign_keys = cursor.fetchall()
            
            print("\n📋 Foreign Keys encontradas:")
            if not foreign_keys:
                print("   No se encontraron foreign keys en las tablas del sistema.")
                return []
            
            for fk in foreign_keys:
                print(f"   {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']} (Constraint: {fk['CONSTRAINT_NAME']})")
            
            return foreign_keys
            
    except Exception as e:
        print(f"❌ Error al listar foreign keys: {e}")
        return []

def eliminar_foreign_key(conexion, tabla, constraint_name):
    """Elimina una foreign key específica."""
    try:
        with conexion.cursor() as cursor:
            query = f"ALTER TABLE {tabla} DROP FOREIGN KEY {constraint_name}"
            print(f"   Ejecutando: {query}")
            cursor.execute(query)
            conexion.commit()
            print(f"   ✅ Foreign key {constraint_name} eliminada de {tabla}")
            return True
            
    except Exception as e:
        print(f"   ❌ Error al eliminar foreign key {constraint_name} de {tabla}: {e}")
        return False

def modificar_columnas_usuarios(conexion):
    """Modifica las columnas id_usuario para que no sean foreign keys."""
    try:
        print("\n🔧 Modificando estructura de columnas...")
        
        modificaciones = [
            {
                "tabla": "consultas",
                "columna": "id_usuario",
                "definicion": "INT NOT NULL COMMENT 'ID de usuario (sin foreign key)'"
            },
            {
                "tabla": "feedback_respuesta", 
                "columna": "id_usuario",
                "definicion": "INT NOT NULL COMMENT 'ID de usuario (sin foreign key)'"
            }
        ]
        
        with conexion.cursor() as cursor:
            for mod in modificaciones:
                query = f"ALTER TABLE {mod['tabla']} MODIFY COLUMN {mod['columna']} {mod['definicion']}"
                print(f"   Ejecutando: {query}")
                cursor.execute(query)
                print(f"   ✅ Columna {mod['tabla']}.{mod['columna']} modificada")
        
        conexion.commit()
        print("✅ Todas las columnas modificadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al modificar columnas: {e}")
        conexion.rollback()
        return False

def verificar_estructura_final(conexion):
    """Verifica que la estructura final sea correcta."""
    try:
        print("\n🔍 Verificando estructura final...")
        
        # Verificar que no hay foreign keys
        foreign_keys = listar_foreign_keys(conexion)
        if foreign_keys:
            print("⚠️  Aún existen foreign keys. La migración puede no haber sido completa.")
        else:
            print("✅ No se encontraron foreign keys relacionadas con usuarios.")
        
        # Verificar estructura de columnas
        with conexion.cursor() as cursor:
            for tabla in ['consultas', 'feedback_respuesta']:
                cursor.execute(f"DESCRIBE {tabla}")
                columnas = cursor.fetchall()
                
                for col in columnas:
                    if col['Field'] == 'id_usuario':
                        print(f"   {tabla}.id_usuario: {col['Type']} {col['Null']} {col['Key']} {col['Extra']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al verificar estructura: {e}")
        return False

def main():
    """Función principal del script de migración."""
    print("🚀 SCRIPT DE MIGRACIÓN MYSQL - ELIMINACIÓN DE FOREIGN KEYS")
    print("=" * 60)
    
    # Verificar que estamos configurados para MySQL
    db_type = os.getenv("DB_TYPE", "sqlite")
    if db_type.lower() != "mysql":
        print(f"⚠️  DB_TYPE está configurado como '{db_type}'. Este script es para MySQL.")
        respuesta = input("¿Continuar de todas formas? (s/N): ")
        if respuesta.lower() != 's':
            print("❌ Operación cancelada.")
            return False
    
    # Conectar a MySQL
    conexion = conectar_mysql()
    if not conexion:
        print("❌ No se pudo conectar a MySQL. Verificar configuración.")
        return False
    
    try:
        print(f"\n📊 Base de datos actual: {DB_NAME}")
        
        # Listar foreign keys existentes
        foreign_keys = listar_foreign_keys(conexion)
        
        if not foreign_keys:
            print("✅ No hay foreign keys que eliminar. La base ya está migrada.")
            return True
        
        # Confirmar operación
        print(f"\n⚠️  Se van a eliminar {len(foreign_keys)} foreign key(s).")
        confirmar = input("¿Proceder con la migración? (s/N): ")
        if confirmar.lower() != 's':
            print("❌ Operación cancelada por el usuario.")
            return False
        
        # Deshabilitar verificación de foreign keys temporalmente
        print("\n🔧 Deshabilitando verificación de foreign keys...")
        with conexion.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            conexion.commit()
        
        # Eliminar foreign keys
        print("\n🗑️  Eliminando foreign keys...")
        exito = True
        for fk in foreign_keys:
            if not eliminar_foreign_key(conexion, fk['TABLE_NAME'], fk['CONSTRAINT_NAME']):
                exito = False
        
        # Modificar estructura de columnas
        if exito:
            modificar_columnas_usuarios(conexion)
        
        # Rehabilitar verificación de foreign keys
        print("\n🔧 Rehabilitando verificación de foreign keys...")
        with conexion.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conexion.commit()
        
        # Verificar resultado
        verificar_estructura_final(conexion)
        
        if exito:
            print("\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("✅ La base de datos MySQL ahora es compatible con la aplicación.")
            print("✅ Las consultas pueden usar id_usuario sin foreign key constraints.")
        else:
            print("\n⚠️  MIGRACIÓN COMPLETADA CON ERRORES")
            print("   Revisar los mensajes anteriores para identificar problemas.")
        
        return exito
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE LA MIGRACIÓN: {e}")
        print(traceback.format_exc())
        return False
        
    finally:
        if conexion:
            conexion.close()
            print("\n🔌 Conexión a MySQL cerrada.")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 