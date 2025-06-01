#!/usr/bin/env python
# BD_RELA/add_test_query_mysql.py
import os
import sys
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def add_test_query_to_mysql():
    """Añadir una consulta de prueba a MySQL para poder probar el feedback"""
    print("=== AÑADIENDO CONSULTA DE PRUEBA A MYSQL ===")
    
    try:
        # Parámetros de conexión desde .env
        host = os.getenv('BD_SERVER', 'mysqldesa.pami.ar')
        port = int(os.getenv('BD_PORT', 3306))
        user = os.getenv('BD_USER')
        password = os.getenv('BD_PASSWD')
        database = os.getenv('BD_NAME')
        
        print(f"Conectando a MySQL: {host}:{port} - {database}")
        
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
        
        cursor = conn.cursor()
        
        # Primero verificar/crear el usuario necesario
        cursor.execute("SELECT id_usuario FROM usuarios WHERE id_usuario = %s", (321,))
        user_result = cursor.fetchone()
        
        if not user_result:
            print("⚠️  Usuario con ID 321 no existe. Creándolo...")
            cursor.execute("""
                INSERT INTO usuarios (id_usuario, nombre, ugel_origen)
                VALUES (%s, %s, %s)
            """, (321, "Usuario de Prueba", "Formosa"))
            print("✅ Usuario creado con ID: 321")
        else:
            print("✅ Usuario con ID 321 ya existe")
        
        # Verificar si hay prompts activos
        cursor.execute("SELECT id_prompt FROM prompts WHERE activo = 1 LIMIT 1")
        prompt_result = cursor.fetchone()
        
        if not prompt_result:
            print("⚠️  No hay prompts activos. Añadiendo uno...")
            cursor.execute("""
                INSERT INTO prompts (nombre_prompt, contenido_prompt, version, activo, fecha_creacion)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                "Prompt de Prueba",
                "Eres un asistente útil. Responde las preguntas de manera clara y concisa.",
                "1.0",
                1,
                datetime.now()
            ))
            prompt_id = cursor.lastrowid
            print(f"✅ Prompt creado con ID: {prompt_id}")
        else:
            prompt_id = prompt_result['id_prompt']
            print(f"✅ Usando prompt existente con ID: {prompt_id}")
        
        # Datos de la consulta de prueba
        test_data = {
            'timestamp': datetime.now(),
            'id_usuario': 321,
            'ugel_origen': 'Formosa',
            'pregunta_usuario': '¿Cómo puedo solicitar un trámite en PAMI?',
            'respuesta_asistente': 'Para solicitar un trámite en PAMI, puede dirigirse a cualquier oficina de PAMI o realizar el trámite en línea a través del sitio web oficial.',
            'respuesta_es_vacia': False,
            'respuesta_util': None,  # Sin feedback inicial
            'id_prompt_usado': prompt_id,
            'tokens_input': 25,
            'tokens_output': 35,
            'tiempo_respuesta_ms': 2500,
            'error_detectado': False,
            'tipo_error': None,
            'mensaje_error': None,
            'origen_canal': 'web',
            'modelo_llm_usado': 'gpt-3.5-turbo',
            'comentario': None
        }
        
        # Insertar la consulta de prueba
        insert_query = """
            INSERT INTO consultas (
                timestamp, id_usuario, ugel_origen, pregunta_usuario, respuesta_asistente,
                respuesta_es_vacia, respuesta_util, id_prompt_usado, tokens_input, tokens_output,
                tiempo_respuesta_ms, error_detectado, tipo_error, mensaje_error, origen_canal,
                modelo_llm_usado, comentario
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cursor.execute(insert_query, (
            test_data['timestamp'], test_data['id_usuario'], test_data['ugel_origen'],
            test_data['pregunta_usuario'], test_data['respuesta_asistente'],
            test_data['respuesta_es_vacia'], test_data['respuesta_util'], 
            test_data['id_prompt_usado'], test_data['tokens_input'], test_data['tokens_output'],
            test_data['tiempo_respuesta_ms'], test_data['error_detectado'], 
            test_data['tipo_error'], test_data['mensaje_error'], test_data['origen_canal'],
            test_data['modelo_llm_usado'], test_data['comentario']
        ))
        
        # Obtener el ID de la consulta insertada
        consulta_id = cursor.lastrowid
        
        # Commit de la transacción
        conn.commit()
        
        print(f"✅ Consulta de prueba insertada con ID: {consulta_id}")
        
        # Verificar la inserción
        cursor.execute("SELECT id_consulta, pregunta_usuario, respuesta_util FROM consultas WHERE id_consulta = %s", (consulta_id,))
        verificacion = cursor.fetchone()
        
        if verificacion:
            print(f"✅ Verificación exitosa:")
            print(f"   ID: {verificacion['id_consulta']}")
            print(f"   Pregunta: {verificacion['pregunta_usuario'][:50]}...")
            print(f"   respuesta_util: {verificacion['respuesta_util']}")
            print(f"\n🎯 Ahora puedes probar el feedback usando el ID: {consulta_id}")
            print(f"   URL de prueba: http://localhost:8000/static/asistente.html")
            print(f"   Haz una pregunta, obtén una respuesta, y prueba los radio buttons")
        else:
            print("❌ Error: No se pudo verificar la inserción")
        
        cursor.close()
        conn.close()
        print("✅ Conexión cerrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feedback_update(consulta_id):
    """Probar el update de feedback directamente en la base de datos"""
    print(f"\n=== PROBANDO UPDATE DE FEEDBACK EN CONSULTA {consulta_id} ===")
    
    try:
        # Parámetros de conexión desde .env
        host = os.getenv('BD_SERVER', 'mysqldesa.pami.ar')
        port = int(os.getenv('BD_PORT', 3306))
        user = os.getenv('BD_USER')
        password = os.getenv('BD_PASSWD')
        database = os.getenv('BD_NAME')
        
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
        
        cursor = conn.cursor()
        
        # Estado inicial
        cursor.execute("SELECT respuesta_util FROM consultas WHERE id_consulta = %s", (consulta_id,))
        before = cursor.fetchone()
        print(f"Estado ANTES: {before}")
        
        # Realizar update a "si"
        cursor.execute("""
            UPDATE consultas 
            SET respuesta_util = %s 
            WHERE id_consulta = %s
        """, ("si", consulta_id))
        
        rows_affected = cursor.rowcount
        print(f"Filas afectadas: {rows_affected}")
        
        # Commit
        conn.commit()
        
        # Verificar cambio
        cursor.execute("SELECT respuesta_util FROM consultas WHERE id_consulta = %s", (consulta_id,))
        after = cursor.fetchone()
        print(f"Estado DESPUÉS: {after}")
        
        if after['respuesta_util'] == "si":
            print("✅ UPDATE a 'si' exitoso!")
            
            # Ahora cambiar a "no"
            cursor.execute("""
                UPDATE consultas 
                SET respuesta_util = %s 
                WHERE id_consulta = %s
            """, ("no", consulta_id))
            
            conn.commit()
            
            cursor.execute("SELECT respuesta_util FROM consultas WHERE id_consulta = %s", (consulta_id,))
            final = cursor.fetchone()
            print(f"Estado FINAL (cambiado a 'no'): {final}")
            
            if final['respuesta_util'] == "no":
                print("✅ UPDATE a 'no' también exitoso!")
                print("🎯 El mecanismo de feedback funciona correctamente en MySQL")
            else:
                print("❌ Error en el segundo UPDATE")
        else:
            print("❌ Error en el primer UPDATE")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Iniciando proceso de añadir consulta de prueba a MySQL...")
    
    success = add_test_query_to_mysql()
    
    if success:
        print("\n" + "="*60)
        print("✅ CONSULTA DE PRUEBA AÑADIDA EXITOSAMENTE")
        print("="*60)
        print("Ahora puedes:")
        print("1. Iniciar el servidor FastAPI: python -m uvicorn app.main:app --reload")
        print("2. Abrir: http://localhost:8000/static/asistente.html")
        print("3. Hacer una consulta para obtener un ID de consulta válido")
        print("4. Probar los radio buttons de feedback")
        print("\nO si quieres probar el mecanismo de feedback directamente:")
        
        # Obtener el último ID insertado para la prueba
        try:
            host = os.getenv('BD_SERVER', 'mysqldesa.pami.ar')
            port = int(os.getenv('BD_PORT', 3306))
            user = os.getenv('BD_USER')
            password = os.getenv('BD_PASSWD')
            database = os.getenv('BD_NAME')
            
            conn = pymysql.connect(
                host=host, port=port, user=user, password=password,
                database=database, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id_consulta) as max_id FROM consultas")
            result = cursor.fetchone()
            if result and result['max_id']:
                last_id = result['max_id']
                print(f"5. Probar feedback directamente con ID {last_id}")
                cursor.close()
                conn.close()
                
                test_feedback_update(last_id)
        except:
            pass
    else:
        print("❌ Error al añadir consulta de prueba") 