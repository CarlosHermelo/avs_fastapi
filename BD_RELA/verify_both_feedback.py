#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('local_database.db')
cursor = conn.cursor()

print("Verificando feedback de las consultas:")
print("-" * 50)

# Verificar consulta 41 (debería ser "si")
cursor.execute('SELECT id_consulta, respuesta_util FROM consultas WHERE id_consulta = 41')
result = cursor.fetchone()
if result:
    print(f"Consulta ID 41: respuesta_util = '{result[1]}' (debería ser 'si')")
else:
    print("Consulta ID 41 no encontrada")

# Verificar consulta 40 (debería ser "no")
cursor.execute('SELECT id_consulta, respuesta_util FROM consultas WHERE id_consulta = 40')
result = cursor.fetchone()
if result:
    print(f"Consulta ID 40: respuesta_util = '{result[1]}' (debería ser 'no')")
else:
    print("Consulta ID 40 no encontrada")

print("-" * 50)
print("✅ Verificación completada")

conn.close() 