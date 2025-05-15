#!/usr/bin/env python
# BD_RELA/listar_consultas_simple.py
import sys
import os
from sqlalchemy import select, desc, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import textwrap

# Importar módulos necesarios desde el mismo directorio
from create_tables import Consulta, get_engine

def listar_consultas(limit=20):
    """
    Lista las consultas almacenadas en la base de datos en formato simple.
    """
    try:
        # Obtener motor y crear sesión
        engine = get_engine()
        
        # Detectar tipo de base de datos
        db_type = engine.name.upper()  # sqlite o mysql
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print(f"\n{'='*80}")
        print(f"LISTADO DE CONSULTAS - Base de datos: {db_type}")
        print(f"{'='*80}")
        
        # Verificar si la tabla existe
        inspector = inspect(engine)
        if "consultas" not in inspector.get_table_names():
            print("La tabla 'consultas' no existe en la base de datos.")
            return
        
        # Construir la consulta
        query = select(Consulta).order_by(desc(Consulta.timestamp))
        
        # Ejecutar consulta con límite
        resultados = session.execute(query.limit(limit)).scalars().all()
        
        if not resultados:
            print("No se encontraron registros en la tabla consultas")
            return
        
        print("ID | Fecha/Hora | ID Usuario | UGL | Pregunta (40 chars) | Respuesta (40 chars)")
        print("-" * 80)
        
        for consulta in resultados:
            # Formatear pregunta y respuesta
            pregunta = textwrap.shorten(consulta.pregunta_usuario, width=40, placeholder="...")
            respuesta = textwrap.shorten(consulta.respuesta_asistente or "", width=40, placeholder="...")
            
            # Imprimir línea de datos
            print(f"{consulta.id_consulta} | {consulta.timestamp.strftime('%Y-%m-%d %H:%M')} | {consulta.id_usuario} | {consulta.ugel_origen} | {pregunta} | {respuesta}")
        
        print(f"\nTotal de registros: {len(resultados)}")
        
        # Cerrar sesión
        session.close()
        
    except Exception as e:
        print(f"Error al consultar la base de datos: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    listar_consultas() 