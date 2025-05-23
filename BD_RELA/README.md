# Base de Datos Relacional

Este módulo contiene los scripts necesarios para la creación y gestión de la base de datos relacional. El sistema está diseñado para funcionar con MySQL en producción y, automáticamente, con SQLite de forma local cuando no se puede conectar a MySQL.

## Configuración

La configuración de conexión a la base de datos se encuentra en el archivo `.env` en la raíz del proyecto. 
Para que el script funcione correctamente, crea un archivo `.env` con las siguientes variables:

```
# Configuración del tipo de base de datos
# Opciones: mysql, sqlite
DB_TYPE=mysql

# Configuración para MySQL
BD_SERVER=mysqldesa.pami.ar
BD_PORT=3306
BD_NAME=avsp
BD_USER=avsp
BD_PASSWD=Des2025avsp

# Configuración para SQLite
SQLITE_PATH=BD_RELA/local_database.db
```

Si quieres forzar el uso de SQLite localmente, simplemente cambia `DB_TYPE=sqlite`. Cuando esté configurado como `mysql`, el sistema intentará conectarse a MySQL primero, y si falla, automáticamente usará SQLite como fallback.

## Estructura de la base de datos

El script `create_tables.py` crea las siguientes tablas:

1. **usuarios**: Identifica a cada agente que usa el asistente.
2. **prompts**: Gestiona los prompts del asistente con versionado y control de activación.
3. **consultas**: Registra todas las interacciones entre los usuarios y el asistente.
4. **feedback_respuesta**: Permite registrar comentarios u observaciones del usuario.
5. **log_batch_bdv**: Registra cada ejecución del proceso batch que actualiza la base vectorial.
6. **log_arranque_app**: Registra cada vez que se inicia la aplicación y el estado de sus dependencias.

## Uso

Para crear las tablas en la base de datos, ejecuta:

```bash
python BD_RELA/create_tables.py
```

Para crear las tablas e insertar datos de prueba:

```bash
python BD_RELA/create_tables.py --test
```

## Fallback a SQLite

El sistema está diseñado para intentar conectarse a MySQL primero (si `DB_TYPE=mysql`). Si la conexión falla:

1. Automáticamente usará SQLite como alternativa
2. Creará el archivo de base de datos en la ruta especificada en `SQLITE_PATH`
3. Las tablas y relaciones se crearán con la misma estructura
4. Se creará un registro en el log advirtiendo del cambio

## Dependencias

- SQLAlchemy
- PyMySQL (para MySQL)
- Python-dotenv
