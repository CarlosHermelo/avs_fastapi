#!/usr/bin/env python
# BD_RELA/check_feedback.py
import sqlite3

def check_feedback_status():
    """Verificar el estado del campo respuesta_util en las consultas"""
    try:
        conn = sqlite3.connect('local_database.db')
        cursor = conn.cursor()
        
        # Verificar las últimas 5 consultas
        cursor.execute('''
            SELECT id_consulta, respuesta_util, pregunta_usuario 
            FROM consultas 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        
        results = cursor.fetchall()
        
        print("Estado actual de respuesta_util en las últimas 5 consultas:")
        print("-" * 70)
        
        for row in results:
            id_consulta, respuesta_util, pregunta = row
            pregunta_corta = pregunta[:50] + "..." if len(pregunta) > 50 else pregunta
            print(f"ID: {id_consulta} | respuesta_util: '{respuesta_util}' | Pregunta: {pregunta_corta}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_feedback_status() 