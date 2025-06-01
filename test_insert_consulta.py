#!/usr/bin/env python3
# test_insert_consulta.py
"""
Script para probar que podemos insertar consultas sin errores de foreign key.
"""

import sys
import os
from datetime import datetime

# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(__file__))

from app.services.db_service import persistir_consulta

def test_insertar_consulta():
    """Prueba insertar una consulta con id_usuario=321 sin foreign key."""
    
    print("🧪 PRUEBA DE INSERCIÓN DE CONSULTA SIN FOREIGN KEY")
    print("=" * 55)
    
    # Datos de prueba
    datos_consulta = {
        "pregunta_usuario": "¿Cuáles son los requisitos para solicitar un bastón?",
        "respuesta_asistente": "Para solicitar un bastón se requiere orden médica...",
        "id_usuario": 321,  # Este valor NO existe en tabla usuarios
        "ugel_origen": "Formosa",
        "tokens_input": 150,
        "tokens_output": 75,
        "tiempo_respuesta_ms": 2500,
        "id_prompt_usado": "prompt_fallback.txt",
        "modelo_llm_usado": "gpt-4o-mini"
    }
    
    print("📝 Datos a insertar:")
    for key, value in datos_consulta.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔍 Intentando insertar consulta con id_usuario={datos_consulta['id_usuario']}...")
    print("   (Este ID NO existe en la tabla usuarios, pero no debe importar)")
    
    try:
        id_consulta = persistir_consulta(**datos_consulta)
        
        if id_consulta:
            print(f"\n✅ ÉXITO: Consulta insertada con ID: {id_consulta}")
            print("✅ No hubo errores de foreign key constraint")
            print("✅ El sistema funciona correctamente sin depender de tabla usuarios")
            return True
        else:
            print(f"\n❌ ERROR: No se pudo insertar la consulta")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        print("❌ Esto indica que aún hay problemas con foreign keys")
        return False

def test_verificar_insercion():
    """Verifica que la consulta se insertó correctamente."""
    try:
        import sqlite3
        
        sqlite_path = "BD_RELA/local_database.db"
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM consultas WHERE id_usuario = 321")
        count = cursor.fetchone()[0]
        
        print(f"\n📊 Consultas con id_usuario=321 en BD: {count}")
        
        if count > 0:
            cursor.execute("""
                SELECT id_consulta, pregunta_usuario, respuesta_asistente, id_usuario, ugel_origen 
                FROM consultas 
                WHERE id_usuario = 321 
                ORDER BY id_consulta DESC 
                LIMIT 1
            """)
            ultima = cursor.fetchone()
            
            print("📋 Última consulta insertada:")
            print(f"   ID: {ultima[0]}")
            print(f"   Pregunta: {ultima[1][:50]}...")
            print(f"   ID Usuario: {ultima[3]}")
            print(f"   UGL: {ultima[4]}")
        
        conn.close()
        return count > 0
        
    except Exception as e:
        print(f"❌ Error verificando inserción: {e}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS DE BASE DE DATOS SIN FOREIGN KEYS")
    print("=" * 60)
    
    # Probar inserción
    exito_insercion = test_insertar_consulta()
    
    # Verificar que se insertó
    if exito_insercion:
        exito_verificacion = test_verificar_insercion()
        
        if exito_verificacion:
            print("\n🎉 TODAS LAS PRUEBAS EXITOSAS")
            print("✅ La migración sin foreign keys funciona perfectamente")
            print("✅ Cuando cambies a MySQL, ejecuta: python BD_RELA/migrate_mysql_remove_fk.py")
        else:
            print("\n⚠️  Inserción exitosa pero verificación falló")
    else:
        print("\n❌ PRUEBAS FALLIDAS")
        print("❌ Revisar configuración de base de datos")
    
    print("\n" + "=" * 60) 