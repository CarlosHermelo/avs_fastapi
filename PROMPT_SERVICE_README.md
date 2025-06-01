# Servicio de Prompt Dinámico

Este documento explica cómo funciona el nuevo servicio de prompt dinámico que permite cargar el prompt del sistema desde una base de datos relacional con fallbacks automáticos.

## Características

- ✅ Carga el prompt desde la base de datos (tabla `prompts`)
- ✅ Fallback automático al archivo `prompt_fallback.txt`
- ✅ Fallback final a prompt hardcodeado
- ✅ Compatible con MySQL y SQLite
- ✅ Logging detallado de la fuente del prompt
- ✅ Manejo robusto de errores

## Jerarquía de Fallbacks

El sistema sigue esta jerarquía para obtener el prompt:

1. **Base de datos** - Busca un prompt con `activo = True` en la tabla `prompts`
2. **Archivo** - Lee el contenido de `prompt_fallback.txt`
3. **Hardcodeado** - Usa un prompt por defecto: "Hola, soy tu asistente. ¿En qué puedo ayudarte?"

## Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con:

```env
# Tipo de base de datos: mysql o sqlite
DB_TYPE=sqlite

# Para MySQL (solo si DB_TYPE=mysql)
BD_SERVER=localhost
BD_PORT=3306
BD_NAME=avsp
BD_USER=root
BD_PASSWD=tu_password

# Para SQLite (solo si DB_TYPE=sqlite)
SQLITE_PATH=BD_RELA/local_database.db
```

### Estructura de la Tabla `prompts`

```sql
CREATE TABLE prompts (
    id_prompt INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_prompt VARCHAR(100) NOT NULL,
    contenido_prompt TEXT NOT NULL,
    version VARCHAR(50),
    activo BOOLEAN DEFAULT FALSE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Uso

### 1. Crear las Tablas

```bash
cd BD_RELA
python create_tables.py
```

### 2. Insertar un Prompt de Ejemplo

```bash
cd BD_RELA
python insertar_prompt_ejemplo.py
```

### 3. Probar el Servicio

```bash
python test_prompt_service.py
```

### 4. Usar en el Código

```python
from app.services.prompt_service import get_system_prompt

# Obtener el prompt con información de la fuente
prompt_content, source = get_system_prompt()

print(f"Prompt obtenido desde: {source}")
print(f"Contenido: {prompt_content[:100]}...")
```

## Logging

El sistema registra automáticamente de dónde se obtuvo el prompt:

```
INFO - PROMPT_LOADED: Prompt cargado desde base de datos
INFO - PROMPT_LOADED: Prompt cargado desde archivo prompt_fallback.txt
WARNING - PROMPT_LOADED: Prompt cargado desde constante hardcodeada (fallback final)
```

## Gestión de Prompts

### Insertar un Nuevo Prompt

```python
from BD_RELA.create_tables import Prompt, get_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = get_engine()
Session = sessionmaker(bind=engine)
session = Session()

# Desactivar prompts anteriores
session.query(Prompt).filter(Prompt.activo == True).update({"activo": False})

# Insertar nuevo prompt
nuevo_prompt = Prompt(
    nombre_prompt="Mi Prompt Personalizado",
    contenido_prompt="Tu contenido del prompt aquí...",
    version="v1.0",
    activo=True,
    fecha_creacion=datetime.now()
)

session.add(nuevo_prompt)
session.commit()
session.close()
```

### Activar un Prompt Existente

```python
# Desactivar todos los prompts
session.query(Prompt).update({"activo": False})

# Activar un prompt específico
prompt_a_activar = session.query(Prompt).filter(Prompt.id_prompt == 5).first()
if prompt_a_activar:
    prompt_a_activar.activo = True
    session.commit()
```

## Scripts Útiles

- `test_prompt_service.py` - Prueba el servicio y muestra la fuente del prompt
- `BD_RELA/insertar_prompt_ejemplo.py` - Inserta un prompt de ejemplo desde `prompt_fallback.txt`
- `BD_RELA/mostrar_prompt_activo.py` - Muestra el prompt activo actual
- `BD_RELA/listar_consultas.py` - Lista las consultas registradas

## Solución de Problemas

### Error de Conexión a la Base de Datos

Si hay problemas de conexión, el sistema automáticamente:
1. Intenta con MySQL si está configurado
2. Hace fallback a SQLite
3. Usa el archivo `prompt_fallback.txt`
4. Usa el prompt hardcodeado como último recurso

### Archivo prompt_fallback.txt No Encontrado

El sistema busca el archivo en varias ubicaciones:
- `./prompt_fallback.txt`
- `../prompt_fallback.txt`
- `../../prompt_fallback.txt`
- `{project_root}/prompt_fallback.txt`

### No Hay Prompt Activo en la Base de Datos

Si no hay ningún prompt con `activo = True`, el sistema automáticamente usa el archivo de fallback.

## Integración con el Asistente

El servicio se integra automáticamente con el asistente virtual. La función `get_sistema_prompt_base()` en `endpoints.py` ahora usa el servicio dinámico en lugar de una constante hardcodeada.

Cada vez que se procesa una consulta, se registra en el log de dónde se obtuvo el prompt, permitiendo monitorear el funcionamiento del sistema. 