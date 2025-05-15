#!/usr/bin/env python
# BD_RELA/actualizar_errores.py
import sys
import os
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Importar módulos necesarios desde el mismo directorio
from create_tables import Consulta, get_engine

def actualizar_errores_respuesta_corta():
    """
    Actualiza todas las consultas y marca como error las que tienen respuestas
    con menos de 150 caracteres. También establece respuesta_es_vacia=True para esas consultas.
    """
    try:
        # Obtener motor y crear sesión
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Obtener todas las consultas
        consultas = session.execute(select(Consulta)).scalars().all()
        
        # Contador de actualizaciones
        actualizadas = 0
        
        # Procesar cada consulta
        for consulta in consultas:
            # Calcular longitud de la respuesta
            longitud = len(consulta.respuesta_asistente or '')
            
            # Si la respuesta es corta y no está marcada como error o vacía
            if longitud < 150 and (not consulta.error_detectado or not consulta.respuesta_es_vacia):
                consulta.error_detectado = True
                consulta.respuesta_es_vacia = True  # Marcar como respuesta vacía
                consulta.tipo_error = "Respuesta demasiado corta"
                consulta.mensaje_error = f"La respuesta tiene {longitud} caracteres (mínimo 150)"
                actualizadas += 1
                print(f"Marcando consulta ID {consulta.id_consulta} como error y respuesta vacía (longitud: {longitud} caracteres)")
        
        # Confirmar cambios si hubo actualizaciones
        if actualizadas > 0:
            session.commit()
            print(f"\nSe actualizaron {actualizadas} consultas con errores de respuesta corta.")
        else:
            print("\nNo se encontraron nuevas consultas que necesiten actualización.")
        
        # Cerrar sesión
        session.close()
        
    except Exception as e:
        print(f"Error al actualizar consultas: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Actualizando errores en consultas con respuestas cortas...")
    actualizar_errores_respuesta_corta() 