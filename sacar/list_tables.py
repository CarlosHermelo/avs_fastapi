import sqlite3; conn = sqlite3.connect('BD_RELA/local_database.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\
table\'); print('Tablas en la base de datos:'); [print(f'- {table[0]}') for table in cursor.fetchall()]; conn.close()
