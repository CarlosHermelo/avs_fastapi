# 🔍 Sistema de Diagnóstico - Asistente SIMAP

Este sistema proporciona herramientas completas para diagnosticar y monitorear el estado de la aplicación del Asistente SIMAP. Incluye tanto endpoints web como scripts independientes para verificar todos los componentes del sistema.

## 📋 ¿Qué verifica el sistema?

### ✅ Componentes verificados:

1. **🖥️ Entorno de Ejecución**
   - Detecta si está corriendo en Windows, Linux o Docker
   - Verifica entorno virtual activo en Windows
   - Valida que esté usando el entorno virtual "tot17" recomendado
   - Proporciona recomendaciones específicas por entorno

2. **🚀 Uvicorn (Servidor Web)**
   - Verifica que el servidor esté ejecutándose
   - Obtiene información de versión y proceso

3. **🔍 Qdrant (Base de Datos Vectorial)**
   - Conexión con el servidor Qdrant
   - Existencia de colecciones
   - Funcionalidad de consultas de similitud
   - Tiempo de respuesta

4. **🗄️ Base de Datos Relacional (MySQL/SQLite Dual)**
   - **Lógica de fallback automático**: Intenta MySQL primero, si falla usa SQLite
   - Reporta el estado de ambas bases de datos
   - Indica claramente cuál está activa y por qué
   - Conexión con MySQL o SQLite (según configuración y disponibilidad)
   - Verificación de tablas del sistema
   - Conteo de registros en cada tabla
   - Integridad de la estructura

5. **🤖 OpenAI**
   - Validación de API Key
   - Funcionamiento de embeddings
   - Funcionamiento del modelo de chat (LLM)
   - Tiempos de respuesta

6. **📁 Archivos Críticos**
   - Existencia de scripts principales
   - Archivos de configuración
   - Tamaños y fechas de modificación

7. **⚙️ Variables de Entorno**
   - Configuración de todas las variables necesarias
   - Validación de archivos .env y config.ini

## 🖥️ Entornos de Ejecución Soportados

### 1. **Windows + Virtual Environment "tot17" (Recomendado)**
- **Estado**: ✅ OK
- **Descripción**: Configuración ideal para desarrollo
- **Activación**: `.\\tot17\\Scripts\\activate`
- **Verificación**: El sistema detecta automáticamente si está activo

### 2. **Windows + Otro Virtual Environment**
- **Estado**: ⚠️ WARNING
- **Descripción**: Funcional pero no es el entorno recomendado
- **Recomendación**: Cambiar al entorno "tot17"

### 3. **Windows sin Virtual Environment**
- **Estado**: ⚠️ WARNING  
- **Descripción**: Riesgo de conflictos de dependencias
- **Recomendación**: Activar entorno virtual "tot17"

### 4. **Docker Container**
- **Estado**: ✅ OK
- **Descripción**: Configuración ideal para producción
- **Detección**: Automática mediante indicadores del contenedor

### 5. **Linux**
- **Estado**: ✅ OK
- **Descripción**: Entorno de servidor estándar

## 🗄️ Sistema de Base de Datos Dual

### Lógica de Fallback Automático:

1. **Primer intento: MySQL**
   - Si MySQL está disponible y conecta → **Estado: OK**
   - Configuración óptima para producción

2. **Fallback: SQLite**
   - Si MySQL falla → Intenta automáticamente con SQLite
   - Si SQLite conecta → **Estado: WARNING** (MySQL desactivado)
   - Informa claramente que está usando fallback

3. **Ambos fallan**
   - **Estado: ERROR**
   - No hay conexión disponible a base de datos

### Interpretación de estados:

| Estado | Base Activa | Significado |
|--------|-------------|-------------|
| **✅ OK** | MySQL | Configuración óptima, MySQL funcionando |
| **⚠️ WARNING** | SQLite | MySQL desactivado/no disponible, usando SQLite como respaldo |
| **❌ ERROR** | Ninguna | No se pudo conectar a ninguna base de datos |

## 🌐 Uso desde el Navegador Web

### Prerrequisitos
- La aplicación FastAPI debe estar ejecutándose
- Uvicorn debe estar activo en el puerto configurado (normalmente 8000)

### Endpoints disponibles:

#### 1. **Diagnóstico Completo HTML**
```
http://localhost:8000/api/health
```
- Interfaz visual completa con Bootstrap
- Muestra estado de todos los componentes incluido el entorno de ejecución
- Información destacada sobre base de datos dual
- Actualización automática en caso de errores
- Código de colores para fácil identificación

#### 2. **Diagnóstico JSON**
```
http://localhost:8000/api/health/json
```
- Datos estructurados en formato JSON
- Incluye información detallada del entorno de ejecución
- Detalles de estado de MySQL y SQLite
- Útil para integración con sistemas de monitoreo

#### 3. **Estado Básico**
```
http://localhost:8000/api/status
```
- Verificación rápida de componentes críticos
- Respuesta ligera para checks de salud

### Ejemplo de uso:
1. Abrir navegador
2. Ir a `http://localhost:8000/api/health`
3. Revisar el reporte visual completo
4. Observar el estado del entorno de ejecución en la sección destacada
5. Verificar qué base de datos está activa (MySQL/SQLite)

## 💻 Uso desde Línea de Comandos (CMD)

### Script Independiente: `diagnostico_sistema.py`

Este script puede ejecutarse **sin necesidad de que FastAPI esté ejecutándose**, lo que lo hace ideal para:
- Verificaciones antes de iniciar la aplicación
- Diagnósticos cuando la aplicación no responde
- Verificación del entorno virtual en Windows
- Automatización de verificaciones
- Integración en scripts de deployment

### Comandos disponibles:

#### 1. **Diagnóstico Básico**
```cmd
python diagnostico_sistema.py
```
- Ejecuta todas las verificaciones incluido entorno y base de datos dual
- Muestra resultado en consola con colores
- Salida legible para humanos

#### 2. **Diagnóstico Detallado**
```cmd
python diagnostico_sistema.py --verbose
```
- Incluye información técnica detallada
- Muestra configuraciones específicas del entorno
- Detalles de las pruebas de conexión MySQL/SQLite
- Útil para debugging

#### 3. **Salida en JSON**
```cmd
python diagnostico_sistema.py --json
```
- Genera output en formato JSON
- Incluye toda la información del entorno de ejecución
- Estado detallado de ambas bases de datos
- Útil para procesamiento automatizado

#### 4. **Guardar Resultado en Archivo**
```cmd
python diagnostico_sistema.py --json --output diagnostico_resultado.json
```
- Guarda el resultado en un archivo
- Útil para auditorías o reportes

#### 5. **Ayuda**
```cmd
python diagnostico_sistema.py --help
```
- Muestra todas las opciones disponibles
- Ejemplos de uso

### Ejemplos prácticos:

#### Verificación de entorno antes de iniciar:
```cmd
# Verificar que el entorno virtual "tot17" esté activo
python diagnostico_sistema.py --verbose

# Verificar código de salida
if %errorlevel% neq 0 (
    echo "Sistema no está listo para desarrollo"
    echo "Activar entorno virtual: .\tot17\Scripts\activate"
    exit /b 1
)

# Si todo está OK, iniciar la aplicación
python app/main.py
```

#### Verificación de base de datos:
```cmd
# Verificar estado de MySQL/SQLite
python diagnostico_sistema.py --json | findstr "database_dual_connection"
```

#### Verificación en Docker:
```cmd
# Dentro del contenedor Docker
python diagnostico_sistema.py --verbose
# Debería detectar automáticamente que está en Docker
```

## 🎨 Interpretación de Resultados

### Estados posibles:

| Estado | Icono | Color | Descripción |
|--------|-------|-------|-------------|
| **OK** | ✅ | Verde | Componente funcionando correctamente |
| **WARNING** | ⚠️ | Amarillo | Componente funcional pero con advertencias |
| **ERROR** | ❌ | Rojo | Componente con problemas críticos |

### Códigos de salida (CMD):
- **0**: Todo OK
- **1**: Advertencias (sistema funcional)
- **2**: Errores críticos
- **130**: Interrumpido por usuario (Ctrl+C)

### Estados específicos del entorno:

#### Entorno de Ejecución:
- **Windows + tot17** = ✅ OK (Recomendado para desarrollo)
- **Windows + otro venv** = ⚠️ WARNING 
- **Windows sin venv** = ⚠️ WARNING
- **Docker** = ✅ OK (Recomendado para producción)
- **Linux** = ✅ OK

#### Base de Datos Dual:
- **MySQL activo** = ✅ OK
- **SQLite activo (MySQL desactivado)** = ⚠️ WARNING
- **Ninguna base disponible** = ❌ ERROR

## 🛠️ Solución de Problemas Comunes

### Error: "Windows SIN entorno virtual activo"
**Causa**: No hay entorno virtual activado en Windows
**Solución**: 
```cmd
# Activar entorno virtual tot17
cd /ruta/a/tu/proyecto
.\tot17\Scripts\activate
python diagnostico_sistema.py
```

### Warning: "Conectado a SQLite (MySQL desactivado)"
**Causa**: MySQL no está disponible, usando SQLite como fallback
**Solución**:
```cmd
# Verificar si MySQL está instalado y ejecutándose
# En Windows (XAMPP/WAMP):
net start mysql

# En Docker:
docker run --name mysql -e MYSQL_ROOT_PASSWORD=password -d mysql:8.0

# Verificar configuración en config.ini:
# BD_SERVER=localhost
# BD_PORT=3306
# BD_USER=root
# BD_PASSWD=tu_password
```

### Error: "Uvicorn no responde"
**Causa**: La aplicación FastAPI no está ejecutándose
**Solución**: 
```cmd
# Asegurarse de que el entorno virtual esté activo
.\tot17\Scripts\activate

# Iniciar la aplicación
cd /ruta/a/tu/proyecto
python app/main.py
```

### Error: "Qdrant no conecta"
**Causa**: Servidor Qdrant no está activo
**Solución**:
```cmd
# En Windows, verificar si Qdrant está ejecutándose
netstat -an | findstr :6333

# En Docker:
docker run -p 6333:6333 qdrant/qdrant

# Verificar configuración en config.ini o .env:
# QDRANT_URL=http://localhost:6333
```

### Error: "OpenAI API Key"
**Causa**: API Key no configurada o inválida
**Solución**:
1. Verificar que OPENAI_API_KEY esté en config.ini o .env
2. Validar que la key sea correcta y tenga créditos
3. Verificar conexión a internet

### Error: "Archivos críticos faltantes"
**Causa**: Estructura del proyecto incompleta
**Solución**:
```cmd
# Verificar que estás en el directorio correcto del proyecto
# Restaurar archivos desde git o backup
git status
git checkout -- archivo_faltante.py
```

## 📊 Ejemplo de Reporte

### Diagnóstico CMD con entorno Windows + tot17:
```
🔍 DIAGNÓSTICO DEL SISTEMA - ASISTENTE SIMAP
============================================================

🖥️ Entorno de Ejecución:
✅ Ejecutándose en Windows con entorno virtual 'tot17' activo

🐍 Python y Entorno:
✅ Entorno Python configurado correctamente

⚙️ Variables de Entorno:
✅ Variables de entorno verificadas: 5/5 configuradas

📁 Archivos Críticos:
✅ Archivos críticos verificados: 7/7 encontrados

🔍 Qdrant (Base Vectorial):
✅ Qdrant conectado correctamente

🗄️ Base de Datos (MySQL/SQLite):
⚠️ Conectado a SQLite (MySQL desactivado/no disponible - fallback activo)

🤖 OpenAI:
✅ OpenAI conectado y funcionando

============================================================
📋 RESUMEN DEL DIAGNÓSTICO
============================================================
⚠️ Estado General del Sistema: WARNING
✅ Verificaciones exitosas: 5
⚠️ Advertencias: 2
❌ Errores: 0
⏱️ Tiempo de ejecución: 3.45 segundos

🖥️ ENTORNO: Windows + Virtual Environment (tot17) ✅

⚠️ ADVERTENCIAS:
  • Entorno de Ejecución: Ejecutándose en Windows con entorno virtual 'tot17' activo
  • Base de Datos (MySQL/SQLite): Conectado a SQLite (MySQL desactivado/no disponible - fallback activo)

⚠️ Sistema funcionando con advertencias
```

### Diagnóstico en Docker:
```
🔍 DIAGNÓSTICO DEL SISTEMA - ASISTENTE SIMAP
============================================================

🖥️ Entorno de Ejecución:
✅ Ejecutándose en contenedor Docker

🗄️ Base de Datos (MySQL/SQLite):
✅ Conectado a MySQL (base de datos principal)

🐳 ENTORNO: Docker Container

🎉 ¡Sistema funcionando correctamente!
```

## 🔄 Automatización y Monitoreo

### Script para verificación de entorno en Windows:
```cmd
@echo off
echo Verificando entorno de desarrollo...

# Verificar que tot17 esté activo
python diagnostico_sistema.py --json > temp_diag.json
findstr "tot17" temp_diag.json >nul
if errorlevel 1 (
    echo ⚠️ ADVERTENCIA: Entorno virtual tot17 no está activo
    echo Ejecutar: .\tot17\Scripts\activate
    pause
)

echo ✅ Entorno verificado
del temp_diag.json
```

### Monitoreo de base de datos dual:
```cmd
@echo off
python diagnostico_sistema.py --json | findstr "active_connection" > db_status.txt
set /p db_status=<db_status.txt

if "%db_status%"=="MySQL" (
    echo ✅ Usando MySQL - Configuración óptima
) else if "%db_status%"=="SQLite" (
    echo ⚠️ Usando SQLite - MySQL no disponible
    echo Considerar activar MySQL para mejor rendimiento
) else (
    echo ❌ No hay conexión a base de datos
)
```

### Integración con Task Scheduler (Windows):
1. Abrir Task Scheduler
2. Crear nueva tarea: "Diagnóstico SIMAP"
3. Configurar trigger (ej: cada hora)
4. Acción: ejecutar `python diagnostico_sistema.py --json --output C:\logs\diagnostico_%date%.json`
5. Configurar alertas basadas en códigos de salida

## 📞 Soporte

Si encuentras problemas con el sistema de diagnóstico:

1. **Ejecuta diagnóstico detallado**: `python diagnostico_sistema.py --verbose`
2. **Verifica el entorno de ejecución**: Confirma que estés en el entorno correcto (tot17 en Windows)
3. **Revisa la configuración de base de datos**: Verifica config.ini para MySQL/SQLite
4. **Revisa logs de la aplicación**: Archivos .log en el directorio del proyecto
5. **Consulta documentación**: README principal del proyecto

### Problemas específicos por entorno:

#### Windows:
- Verificar que el entorno virtual "tot17" esté activo
- Comprobar que MySQL esté instalado (XAMPP/WAMP) si se requiere
- Verificar permisos de escritura en directorios del proyecto

#### Docker:
- Verificar que los volúmenes estén montados correctamente
- Comprobar conectividad de red entre contenedores
- Revisar que requirements.txt esté actualizado

---

**Autor**: Sistema SIMAP  
**Última actualización**: 2025  
**Versión**: 2.0 - Entorno Dual y Detección Automática 