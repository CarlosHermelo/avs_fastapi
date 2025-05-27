#!/usr/bin/env python
# BD_RELA/update_feedback_manual.py
import sqlite3

def update_feedback_manual():
    """Actualizar manualmente el feedback para probar la funcionalidad"""
    
    try:
        conn = sqlite3.connect('local_database.db')
        cursor = conn.cursor()
        
        # Verificar estado antes del update
        print("Estado ANTES del update:")
        cursor.execute('SELECT id_consulta, respuesta_util FROM consultas WHERE id_consulta = 41')
        result = cursor.fetchone()
        if result:
            print(f"ID: {result[0]} | respuesta_util: '{result[1]}'")
        else:
            print("Consulta ID 41 no encontrada")
            return
        
        # Realizar el update
        print("\nRealizando UPDATE...")
        cursor.execute('''
            UPDATE consultas 
            SET respuesta_util = ? 
            WHERE id_consulta = ?
        ''', ("si", 41))
        
        # Verificar cuántas filas fueron afectadas
        rows_affected = cursor.rowcount
        print(f"Filas afectadas: {rows_affected}")
        
        # Commit de la transacción
        conn.commit()
        print("Commit realizado")
        
        # Verificar estado después del update
        print("\nEstado DESPUÉS del update:")
        cursor.execute('SELECT id_consulta, respuesta_util FROM consultas WHERE id_consulta = 41')
        result = cursor.fetchone()
        if result:
            print(f"ID: {result[0]} | respuesta_util: '{result[1]}'")
            
            if result[1] == "si":
                print("✅ Update exitoso!")
            else:
                print("❌ Update falló - el valor no cambió")
        else:
            print("❌ Consulta no encontrada después del update")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_feedback_manual() 