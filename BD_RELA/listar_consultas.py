#!/usr/bin/env python
# BD_RELA/listar_consultas.py
import sys
import os

# Añadir el directorio raíz del proyecto a sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import select, desc, inspect, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from tabulate import tabulate
import textwrap

from create_tables import Consulta, get_engine

def listar_consultas(limit=20, mostrar_respuesta=False, filtro_error=None, filtro_personalizado=None, formato_tabla=False):
    try:
        engine = get_engine()
        db_type = engine.name.upper()
        Session = sessionmaker(bind=engine)
        session = Session()

        print(f"\n{'='*80}")
        print(f"LISTADO DE CONSULTAS - Base de datos: {db_type}")
        print(f"{'='*80}")

        inspector = inspect(engine)
        if "consultas" not in inspector.get_table_names():
            print("La tabla 'consultas' no existe en la base de datos.")
            return

        query = select(Consulta).order_by(desc(Consulta.timestamp))

        if filtro_error is not None:
            query = query.filter(Consulta.error_detectado == filtro_error)

        resultados = session.execute(query.limit(limit)).scalars().all()

        if filtro_personalizado:
            resultados = [r for r in resultados if filtro_personalizado(r)]

        if not resultados:
            print("No se encontraron registros en la tabla consultas")
            return

        if formato_tabla:
            headers = ["ID", "Fecha", "ID Usuario", "UGEL", "Pregunta", "Respuesta", "¿Vacía?", "¿Error?", "Modelo", "Tokens IN", "Tokens OUT", "Comentario"]
            rows = []
            for consulta in resultados:
                tokens_in = f"{consulta.tokens_input:,}" if consulta.tokens_input else "N/A"
                tokens_out = f"{consulta.tokens_output:,}" if consulta.tokens_output else "N/A"

                rows.append([
                    consulta.id_consulta,
                    consulta.timestamp.strftime("%Y-%m-%d %H:%M"),
                    consulta.id_usuario,
                    consulta.ugel_origen,
                    textwrap.shorten(consulta.pregunta_usuario, width=30, placeholder="..."),
                    (consulta.respuesta_asistente or "")[:50] + ("..." if len(consulta.respuesta_asistente or "") > 50 else ""),
                    "Sí" if consulta.respuesta_es_vacia else "No",
                    "Sí" if consulta.error_detectado else "No",
                    consulta.modelo_llm_usado or "N/A",
                    tokens_in,
                    tokens_out,
                    textwrap.shorten(consulta.comentario or "", width=30, placeholder="...")
                ])
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print(f"\nTotal de registros: {len(resultados)}")
            if not mostrar_respuesta:
                return

        for i, consulta in enumerate(resultados, 1):
            print(f"\nRegistro #{i} - ID: {consulta.id_consulta}")
            print(f"Fecha: {consulta.timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"ID Usuario: {consulta.id_usuario}")
            print(f"UGEL Origen: {consulta.ugel_origen}")
            print(f"Pregunta usuario: {consulta.pregunta_usuario}")
            respuesta_corta = (consulta.respuesta_asistente or "")[:50]
            if len(consulta.respuesta_asistente or "") > 50:
                respuesta_corta += "..."
            print(f"Respuesta asistente: {respuesta_corta}")
            print(f"Respuesta es vacía: {consulta.respuesta_es_vacia}")
            print(f"Respuesta útil: {consulta.respuesta_util}")
            print(f"ID prompt usado: {consulta.id_prompt_usado}")
            print(f"Comentario: {consulta.comentario or 'N/A'}")

            tokens_in = f"{consulta.tokens_input:,}" if consulta.tokens_input else "N/A"
            tokens_out = f"{consulta.tokens_output:,}" if consulta.tokens_output else "N/A"
            tiempo_ms = f"{consulta.tiempo_respuesta_ms:,}" if consulta.tiempo_respuesta_ms else "N/A"

            print(f"Tokens input: {tokens_in}")
            print(f"Tokens output: {tokens_out}")
            print(f"Tiempo respuesta (ms): {tiempo_ms}")
            print(f"Error detectado: {consulta.error_detectado}")
            print(f"Tipo error: {consulta.tipo_error}")
            print(f"Mensaje error: {consulta.mensaje_error}")
            print(f"Origen canal: {consulta.origen_canal}")
            print(f"Modelo LLM usado: {consulta.modelo_llm_usado}")
            print("-" * 50)

        if mostrar_respuesta and not formato_tabla:
            print(f"\n{'='*80}")
            print("DETALLE DE RESPUESTAS COMPLETAS")
            print(f"{'='*80}")
            for i, consulta in enumerate(resultados, 1):
                print(f"\n[{i}] ID: {consulta.id_consulta} - Usuario: {consulta.id_usuario}")
                print(f"Pregunta: {consulta.pregunta_usuario}")
                print("-" * 40)
                print(f"Respuesta: {consulta.respuesta_asistente}")
                print("-" * 40)
                tokens_in = f"{consulta.tokens_input:,}" if consulta.tokens_input else "N/A"
                tokens_out = f"{consulta.tokens_output:,}" if consulta.tokens_output else "N/A"
                print(f"Tokens: {tokens_in} entrada | {tokens_out} salida")
                if consulta.error_detectado:
                    print(f"TIPO ERROR: {consulta.tipo_error}")
                    print(f"MENSAJE ERROR: {consulta.mensaje_error}")

        try:
            total_registros_count = session.query(func.count(Consulta.id_consulta)).scalar()
            print(f"\n{'='*80}")
            print(f"TOTAL DE REGISTROS EN LA TABLA 'consultas': {total_registros_count}")
            print(f"{'='*80}")
        except Exception as e_count:
            print(f"Error al obtener el conteo total de registros: {str(e_count)}")

        session.close()

    except Exception as e:
        print(f"Error al consultar la base de datos: {str(e)}")
        import traceback
        traceback.print_exc()

def mostrar_ayuda():
    print("\nScript para listar registros de la tabla consultas")
    print("\nOpciones:")
    print("  --limit N          Limita el número de registros a mostrar (por defecto 20)")
    print("  --respuestas       Muestra el texto completo de las respuestas")
    print("  --con-errores      Muestra solo consultas con errores")
    print("  --sin-errores      Muestra solo consultas sin errores")
    print("  --respuestas-cortas Muestra solo consultas con respuestas cortas (< 150 caracteres)")
    print("  --formato-tabla    Muestra los resultados en formato tabular compacto")
    print("  --ayuda            Muestra esta ayuda")

if __name__ == "__main__":
    limit = 20
    mostrar_respuesta = False
    filtro_error = None
    filtro_personalizado = None
    formato_tabla = False

    if "--ayuda" in sys.argv:
        mostrar_ayuda()
        sys.exit(0)

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
                i += 2
            except ValueError:
                print("Error: El valor para --limit debe ser un número entero")
                sys.exit(1)
        elif args[i] == "--respuestas":
            mostrar_respuesta = True
            i += 1
        elif args[i] == "--con-errores":
            filtro_error = True
            i += 1
        elif args[i] == "--sin-errores":
            filtro_error = False
            i += 1
        elif args[i] == "--respuestas-cortas":
            def filtro_respuestas_cortas(consulta):
                return len(consulta.respuesta_asistente or '') < 150
            filtro_personalizado = filtro_respuestas_cortas
            i += 1
        elif args[i] == "--formato-tabla":
            formato_tabla = True
            i += 1
        else:
            print(f"Argumento desconocido: {args[i]}")
            mostrar_ayuda()
            sys.exit(1)

    listar_consultas(limit=limit, mostrar_respuesta=mostrar_respuesta, filtro_error=filtro_error, filtro_personalizado=filtro_personalizado, formato_tabla=formato_tabla)
