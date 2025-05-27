#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('local_database.db')
cursor = conn.cursor()

cursor.execute('SELECT id_consulta, respuesta_util FROM consultas WHERE id_consulta = 41')
result = cursor.fetchone()

if result:
    print(f"Consulta ID 41: respuesta_util = '{result[1]}'")
else:
    print("Consulta ID 41 no encontrada")

conn.close() 