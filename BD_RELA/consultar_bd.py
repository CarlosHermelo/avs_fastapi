#!/usr/bin/env python
# BD_RELA/consultar_bd.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from create_tables import get_engine

def consultar_datos():
    """Consulta datos directamente en la base de datos."""
    try:
        # Obtener motor
        engine = get_engine()
        
        # Ejecutar consulta SQL directa
        with engine.connect() as conn:
            # Consultar total de registros
            result = conn.execute(text("SELECT COUNT(*) FROM consultas"))
            total = result.scalar()
            print(f"Total de consultas en la base de datos: {total}")
            
            # Consultar últimas consultas
            result = conn.execute(text("""
                SELECT id_consulta, timestamp, id_usuario, ugel_origen, 
                       pregunta_usuario, respuesta_asistente
                FROM consultas 
                ORDER BY timestamp DESC 
                LIMIT 5
            """))
            
            # Mostrar resultados
            print("\nÚltimas consultas:")
            print("-" * 80)
            
            for row in result:
                print(f"ID: {row.id_consulta} | Fecha: {row.timestamp}")
                print(f"Usuario: {row.id_usuario} | UGL: {row.ugel_origen}")
                print(f"Pregunta: {row.pregunta_usuario[:100]}")
                print(f"Respuesta: {row.respuesta_asistente[:100] if row.respuesta_asistente else 'Sin respuesta'}")
                print("-" * 80)
                
    except Exception as e:
        print(f"Error al consultar la base de datos: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    consultar_datos() 