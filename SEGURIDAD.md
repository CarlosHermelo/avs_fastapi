# 🔒 Guía de Seguridad - Asistente Virtual SIMAP

## ⚠️ Problemas de Seguridad Identificados y Solucionados

### 1. **Logs en el directorio raíz**
- **Problema**: Los archivos de log aparecían en la raíz del proyecto en lugar de la carpeta `logs/`
- **Solución**: Modificado `app/core/logging_config.py` para forzar que todos los logs vayan a `logs/`
- **Estado**: ✅ Solucionado

### 2. **API Keys expuestas en archivos**
- **Problema**: API keys reales estaban expuestas en `config.ini` y archivos `.backup`
- **Solución**: Limpiado `config.ini` y actualizado `.gitignore`
- **Estado**: ✅ Solucionado

### 3. **Variable de entorno inconsistente**
- **Problema**: Múltiples variables para la API key (`api_key`, `OPENAI_API_KEY`, `openai_api_key`)
- **Respuesta**: El código usa `OPENAI_API_KEY` (mayúsculas) como principal, con fallback a `openai_api_key` del config.ini
- **Estado**: ✅ Documentado

## 📋 Variables de Entorno Utilizadas

### **Principal (recomendada)**
```bash
OPENAI_API_KEY=sk-tu-clave-aqui
```

### **Fallback (config.ini)**
```ini
[DEFAULT]
openai_api_key = tu-clave-aqui
```

### **NO usadas (para tu información)**
- `api_key` - No se usa en el código principal
- Otras variaciones en minúsculas

## 🛡️ Configuración Segura

### **1. Usar el script de configuración automática**
```bash
python setup_secure.py
```

### **2. Configuración manual**

#### Paso 1: Crear archivo .env
```bash
cp env.example .env
# Editar .env con tus valores reales
```

#### Paso 2: Verificar permisos
```bash
chmod 600 .env  # Solo el propietario puede leer/escribir
```

#### Paso 3: Verificar .gitignore
El archivo `.gitignore` debe incluir:
```
.env
*.env
.env.*
!env.example
*.backup
*.log
logs/
*api_key*
*secret*
credentials*
```

## 🚫 Archivos que NUNCA deben tener commit

### **Archivos con API keys reales**
- `.env`
- `.env.local`
- `.env.production`
- `*.backup`
- `config.ini` (si contiene keys reales)

### **Archivos de log**
- `*.log`
- `logs/`
- `app_*.log`
- `debug_*.log`

### **Bases de datos locales**
- `*.db`
- `*.sqlite`
- `*.sqlite3`

## ✅ Checklist de Seguridad

Antes de hacer `git push`, verificar:

- [ ] No hay archivos `.log` en el root del proyecto
- [ ] El archivo `config.ini` no contiene API keys reales (solo placeholders)
- [ ] El archivo `.env` está en `.gitignore`
- [ ] No hay archivos `.backup` con API keys
- [ ] Ejecutar `git status` para revisar qué archivos se incluirán
- [ ] Ejecutar `python setup_secure.py` para verificación automática

## 🔧 Comandos de Verificación

### **Verificar estado de Git**
```bash
git status
```

### **Buscar API keys expuestas**
```bash
grep -r "sk-" . --exclude-dir=.git
grep -r "tvly-" . --exclude-dir=.git
```

### **Verificar archivos que se incluirán en el commit**
```bash
git diff --cached --name-only
```

### **Ejecutar verificación automática**
```bash
python setup_secure.py
```

## 🚨 Qué hacer si ya expusiste una API key

### **1. Revocar la API key inmediatamente**
- Ve a tu panel de OpenAI/Tavily
- Revoca la API key expuesta
- Genera una nueva API key

### **2. Limpiar el historial de Git (si es necesario)**
```bash
# Para el último commit
git reset --soft HEAD~1
git add .
git commit -m "Fix: Remove exposed API keys"

# Para commits más antiguos, considera usar git filter-repo
```

### **3. Actualizar configuración**
```bash
python setup_secure.py
```

## 📞 Contacto

Si encuentras problemas de seguridad adicionales, documenta el problema y sigue esta guía para solucionarlo.

---

**⚠️ IMPORTANTE**: Esta configuración de seguridad debe revisarse periódicamente y actualizarse según las mejores prácticas de seguridad. 