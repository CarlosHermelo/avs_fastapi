# 🚀 Guía de Migración de Bases de Datos

Esta guía explica cómo manejar las bases de datos SQLite y MySQL sin depender de foreign keys con la tabla usuarios.

## 📋 Situación Actual

- ✅ **SQLite**: Ya configurado sin foreign keys, funciona perfectamente
- ⚠️ **MySQL**: Puede tener foreign keys que necesitan eliminarse

## 🛠️ Scripts Disponibles

### 1. `verificar_estado_bd.py`
Verifica el estado actual de las bases de datos.

```bash
python BD_RELA/verificar_estado_bd.py
```

**¿Qué hace?**
- Muestra tablas existentes
- Verifica estructura de columnas
- Lista foreign keys existentes
- Cuenta registros en las tablas

### 2. `migrate_mysql_remove_fk.py`
Migra MySQL eliminando foreign keys con usuarios.

```bash
python BD_RELA/migrate_mysql_remove_fk.py
```

**¿Qué hace?**
- Lista foreign keys existentes
- Elimina constraints problemáticos
- Modifica estructura de columnas
- Verifica resultado final

## 📖 Casos de Uso

### Caso 1: Actualmente usas SQLite
```bash
# 1. Verificar que todo esté OK
python BD_RELA/verificar_estado_bd.py

# Resultado esperado: "✅ No hay foreign keys en 'consultas' (correcto para SQLite)"
```

### Caso 2: Cambiar de SQLite a MySQL
```bash
# 1. Cambiar DB_TYPE en .env
# DB_TYPE=mysql

# 2. Verificar estado de MySQL
python BD_RELA/verificar_estado_bd.py

# 3. Si hay foreign keys problemáticos, migrar
python BD_RELA/migrate_mysql_remove_fk.py

# 4. Verificar resultado
python BD_RELA/verificar_estado_bd.py
```

### Caso 3: MySQL ya configurado pero con foreign keys
```bash
# 1. Ejecutar migración
python BD_RELA/migrate_mysql_remove_fk.py

# 2. Verificar resultado
python BD_RELA/verificar_estado_bd.py
```

## ⚙️ Configuración .env

### Para SQLite (actual):
```ini
DB_TYPE=sqlite
SQLITE_PATH=BD_RELA/local_database.db
```

### Para MySQL (futuro):
```ini
DB_TYPE=mysql
BD_SERVER=mysqldesa.pami.ar
BD_PORT=3306
BD_NAME=avsp
BD_USER=tu_usuario
BD_PASSWD=tu_password
```

## 🔍 Verificaciones

### ✅ Estado Correcto SQLite:
```
📊 Estructura tabla 'consultas':
   id_usuario: INTEGER NOT NULL
✅ No hay foreign keys en 'consultas' (correcto para SQLite)
```

### ✅ Estado Correcto MySQL:
```
📊 Estructura tabla 'consultas':
   id_usuario: int(11) NO  
✅ No hay foreign keys en 'consultas' (migración exitosa)
```

### ❌ Estado Problemático MySQL:
```
🔗 Foreign Keys en 'consultas': 1
   id_usuario -> usuarios.id_usuario (consultas_ibfk_1)
```

## 🚨 Solución de Problemas

### Error: "Can't connect to MySQL server"
- Verificar configuración en `.env`
- Verificar que MySQL esté ejecutándose
- Verificar credenciales y permisos

### Error: "Access denied for user"
- Verificar usuario y contraseña en `.env`
- Verificar permisos del usuario en MySQL

### Error durante migración
- El script tiene rollback automático
- Re-ejecutar después de corregir el problema
- Usar `verificar_estado_bd.py` para diagnóstico

## 📈 Beneficios de esta Solución

1. **Flexibilidad**: Mismo código funciona con SQLite y MySQL
2. **Simplicidad**: No dependes de tabla usuarios
3. **Robustez**: No hay errores de foreign key constraints
4. **Escalabilidad**: Fácil migración entre bases de datos

## 🎯 Comandos Rápidos

```bash
# Verificar estado actual
python BD_RELA/verificar_estado_bd.py

# Migrar MySQL si es necesario
python BD_RELA/migrate_mysql_remove_fk.py

# Recrear tablas SQLite
python BD_RELA/create_tables.py

# Crear datos de prueba
python BD_RELA/create_tables.py --test
``` 