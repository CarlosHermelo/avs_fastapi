#!/usr/bin/env python
# BD_RELA/test_mysql_feedback.py
import os
import sys
import pymysql
import sqlite3
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_mysql_connection():
    """Probar la conexión a MySQL y realizar un test de feedback"""
    print("=== PRUEBA DE CONEXIÓN MYSQL ===")
    
    try:
        # Parámetros de conexión desde .env
        host = os.getenv('BD_SERVER', 'mysqldesa.pami.ar')  # Default que vi en los logs
        port = int(os.getenv('BD_PORT', 3306))
        user = os.getenv('BD_USER')
        password = os.getenv('BD_PASSWD')
        database = os.getenv('BD_NAME')
        
        print(f"Intentando conectar a MySQL:")
        print(f"Host: {host}:{port}")
        print(f"User: {user}")
        print(f"Database: {database}")
        print(f"Password: {'*' * len(password) if password else 'None'}")
        
        # Conectar a MySQL
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=60,
            autocommit=False
        )
        
        print("✅ Conexión a MySQL exitosa!")
        
        # Probar una query simple
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"Test query resultado: {result}")
        
        # Verificar la tabla consultas
        cursor.execute("SHOW TABLES LIKE 'consultas'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ Tabla 'consultas' encontrada")
            
            # Contar total de consultas
            cursor.execute("SELECT COUNT(*) as total FROM consultas")
            count_result = cursor.fetchone()
            total_consultas = count_result['total']
            print(f"Total de consultas en MySQL: {total_consultas}")
            
            if total_consultas > 0:
                # Obtener las últimas consultas
                cursor.execute("""
                    SELECT id_consulta, respuesta_util, pregunta_usuario 
                    FROM consultas 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
                
                consultas = cursor.fetchall()
                print(f"\nÚltimas 5 consultas en MySQL:")
                print("-" * 80)
                
                for consulta in consultas:
                    id_consulta = consulta['id_consulta']
                    respuesta_util = consulta['respuesta_util']
                    pregunta = consulta['pregunta_usuario'][:50] + "..." if len(consulta['pregunta_usuario']) > 50 else consulta['pregunta_usuario']
                    print(f"ID: {id_consulta} | respuesta_util: '{respuesta_util}' | Pregunta: {pregunta}")
                
                # Probar un update si hay consultas
                test_id = consultas[0]['id_consulta']
                print(f"\n🧪 Probando UPDATE en consulta ID: {test_id}")
                
                # Verificar estado actual
                cursor.execute("SELECT respuesta_util FROM consultas WHERE id_consulta = %s", (test_id,))
                before = cursor.fetchone()
                print(f"Estado ANTES: {before}")
                
                # Realizar update
                new_value = "si" if before['respuesta_util'] != "si" else "no"
                cursor.execute("""
                    UPDATE consultas 
                    SET respuesta_util = %s 
                    WHERE id_consulta = %s
                """, (new_value, test_id))
                
                rows_affected = cursor.rowcount
                print(f"Filas afectadas: {rows_affected}")
                
                # Commit
                conn.commit()
                print("Commit realizado")
                
                # Verificar estado después
                cursor.execute("SELECT respuesta_util FROM consultas WHERE id_consulta = %s", (test_id,))
                after = cursor.fetchone()
                print(f"Estado DESPUÉS: {after}")
                
                if after['respuesta_util'] == new_value:
                    print("✅ UPDATE exitoso en MySQL!")
                else:
                    print("❌ UPDATE falló en MySQL")
            else:
                print("⚠️  La tabla consultas está vacía en MySQL")
                print("Esto explica por qué el feedback no funciona - no hay consultas para actualizar")
                
        else:
            print("❌ Tabla 'consultas' no encontrada en MySQL")
        
        cursor.close()
        conn.close()
        print("✅ Conexión MySQL cerrada correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en MySQL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sqlite_connection():
    """Probar la conexión a SQLite para comparar"""
    print("\n=== PRUEBA DE CONEXIÓN SQLITE (Para comparar) ===")
    
    try:
        sqlite_path = os.getenv('SQLITE_PATH', 'BD_RELA/local_database.db')
        print(f"Conectando a SQLite: {sqlite_path}")
        
        if not os.path.exists(sqlite_path):
            print(f"❌ Archivo SQLite no encontrado: {sqlite_path}")
            return False
        
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Contar total de consultas
        cursor.execute("SELECT COUNT(*) as total FROM consultas")
        total_consultas = cursor.fetchone()[0]
        print(f"Total de consultas en SQLite: {total_consultas}")
        
        if total_consultas > 0:
            # Obtener las últimas consultas
            cursor.execute("""
                SELECT id_consulta, respuesta_util, pregunta_usuario 
                FROM consultas 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            
            consultas = cursor.fetchall()
            print(f"Últimas 5 consultas en SQLite:")
            print("-" * 80)
            
            for consulta in consultas:
                id_consulta = consulta['id_consulta']
                respuesta_util = consulta['respuesta_util']
                pregunta = consulta['pregunta_usuario'][:50] + "..." if len(consulta['pregunta_usuario']) > 50 else consulta['pregunta_usuario']
                print(f"ID: {id_consulta} | respuesta_util: '{respuesta_util}' | Pregunta: {pregunta}")
        else:
            print("⚠️  La tabla consultas está vacía en SQLite también")
        
        cursor.close()
        conn.close()
        print("✅ SQLite verificado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en SQLite: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Iniciando pruebas de conexión de base de datos...")
    print("\n=== VARIABLES DE ENTORNO ===")
    print(f"DB_TYPE: {os.getenv('DB_TYPE', 'no definido')}")
    print(f"BD_SERVER: {os.getenv('BD_SERVER', 'no definido')}")
    print(f"BD_PORT: {os.getenv('BD_PORT', 'no definido')}")
    print(f"BD_USER: {os.getenv('BD_USER', 'no definido')}")
    print(f"BD_NAME: {os.getenv('BD_NAME', 'no definido')}")
    print(f"BD_PASSWD: {'configurado' if os.getenv('BD_PASSWD') else 'no definido'}")
    print(f"SQLITE_PATH: {os.getenv('SQLITE_PATH', 'no definido')}")
    
    # Verificar variables de entorno
    db_type = os.getenv('DB_TYPE', 'sqlite')
    print(f"\nDB_TYPE actual: {db_type}")
    
    if db_type.lower() == 'mysql':
        mysql_success = test_mysql_connection()
        sqlite_success = test_sqlite_connection()
        
        print(f"\n=== RESUMEN ===")
        print(f"MySQL: {'✅ OK' if mysql_success else '❌ FALLO'}")
        print(f"SQLite: {'✅ OK' if sqlite_success else '❌ FALLO'}")
        
        if mysql_success:
            print("\n🎯 MySQL está funcionando.")
            print("Si los radio buttons no funcionan, el problema puede ser:")
            print("1. La tabla consultas está vacía en MySQL")
            print("2. El frontend no está recibiendo un id_consulta válido")
            print("3. Hay un problema en el endpoint de feedback")
        else:
            print("\n⚠️  MySQL tiene problemas. Revisa la configuración en .env")
    else:
        print("DB_TYPE no está configurado para MySQL. Cambia a DB_TYPE=mysql para probar.")
        sqlite_success = test_sqlite_connection() 