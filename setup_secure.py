#!/usr/bin/env python3
"""
Script de configuración segura para el Asistente Virtual SIMAP
Configura variables de entorno y verificación de seguridad
"""

import os
import sys
from pathlib import Path
import configparser
import getpass

def crear_env_file():
    """Crear archivo .env si no existe"""
    env_path = Path('.env')
    
    if env_path.exists():
        print("⚠️  El archivo .env ya existe.")
        respuesta = input("¿Deseas sobrescribirlo? (s/N): ").lower()
        if respuesta != 's':
            print("❌ Operación cancelada.")
            return False
    
    print("\n🔧 Configurando variables de entorno...")
    
    # Solicitar API Key de OpenAI
    print("\n📝 Configuración de OpenAI:")
    openai_key = getpass.getpass("Ingresa tu API Key de OpenAI (sk-...): ")
    
    if not openai_key.startswith('sk-'):
        print("❌ La API Key de OpenAI debe comenzar con 'sk-'")
        return False
    
    # Configuración de base de datos
    print("\n💾 Configuración de base de datos:")
    print("1. SQLite (recomendado para desarrollo)")
    print("2. MySQL (para producción)")
    db_choice = input("Selecciona tipo de BD (1/2): ").strip()
    
    # Crear contenido del .env
    env_content = f"""# Archivo .env - Configuración del Asistente Virtual SIMAP

# OpenAI API Key (OBLIGATORIA)
OPENAI_API_KEY={openai_key}

# Configuración de la aplicación
OPENAI_MODEL=gpt-4o-mini
ENVIRONMENT=development

# Configuración de Qdrant (Base de datos vectorial)
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=fragment_store
NOMBRE_BDV=fragment_store
MAX_RESULTS=5

# Configuración de usuario (valores fijos)
ID_USUARIO=321
UGEL_ORIGEN=Formosa

"""
    
    if db_choice == "2":
        # Configuración MySQL
        print("\n🗄️  Configuración MySQL:")
        db_host = input("Host de MySQL (localhost): ").strip() or "localhost"
        db_port = input("Puerto de MySQL (3306): ").strip() or "3306"
        db_name = input("Nombre de base de datos (avsp): ").strip() or "avsp"
        db_user = input("Usuario de MySQL (root): ").strip() or "root"
        db_pass = getpass.getpass("Password de MySQL: ")
        
        env_content += f"""# Configuración de Base de Datos MySQL
DB_TYPE=mysql
BD_SERVER={db_host}
BD_PORT={db_port}
BD_NAME={db_name}
BD_USER={db_user}
BD_PASSWD={db_pass}
"""
    else:
        # Configuración SQLite (por defecto)
        env_content += """# Configuración de Base de Datos SQLite
DB_TYPE=sqlite
SQLITE_PATH=BD_RELA/local_database.db
"""
    
    # Escribir archivo .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    # Configurar permisos restrictivos
    os.chmod(env_path, 0o600)
    
    print(f"✅ Archivo .env creado exitosamente con permisos restrictivos")
    return True

def limpiar_config_ini():
    """Limpiar API keys del config.ini"""
    config_path = Path('config.ini')
    
    if not config_path.exists():
        print("✅ config.ini no existe, no hay nada que limpiar")
        return True
    
    print("\n🧹 Limpiando config.ini...")
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
        
        # Limpiar API keys
        if 'DEFAULT' in config:
            if 'openai_api_key' in config['DEFAULT']:
                if config['DEFAULT']['openai_api_key'].startswith('sk-'):
                    config['DEFAULT']['openai_api_key'] = 'tu-clave-openai-aqui'
                    print("🔧 openai_api_key limpiada en config.ini")
            
            if 'tavily_api_key' in config['DEFAULT']:
                if config['DEFAULT']['tavily_api_key'].startswith('tvly-'):
                    config['DEFAULT']['tavily_api_key'] = 'tu-clave-tavily-aqui'
                    print("🔧 tavily_api_key limpiada en config.ini")
        
        # Escribir config.ini limpio
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print("✅ config.ini limpiado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al limpiar config.ini: {e}")
        return False

def verificar_seguridad():
    """Verificar que no hay API keys expuestas"""
    print("\n🔍 Verificando seguridad...")
    
    problemas = []
    
    # Verificar config.ini
    config_path = Path('config.ini')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'sk-' in content:
                problemas.append("config.ini contiene API keys de OpenAI")
            if 'tvly-' in content:
                problemas.append("config.ini contiene API keys de Tavily")
    
    # Verificar archivos .env.backup o similares
    for backup_file in Path('.').glob('*.backup'):
        if backup_file.exists():
            problemas.append(f"Archivo backup encontrado: {backup_file}")
    
    # Verificar logs en root
    for log_file in Path('.').glob('*.log'):
        if log_file.exists():
            problemas.append(f"Archivo de log en root: {log_file}")
    
    if problemas:
        print("⚠️  Problemas de seguridad encontrados:")
        for problema in problemas:
            print(f"   - {problema}")
        return False
    else:
        print("✅ No se encontraron problemas de seguridad")
        return True

def crear_directorio_logs():
    """Crear directorio de logs si no existe"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        logs_dir.mkdir()
        print(f"✅ Directorio logs/ creado")
    else:
        print(f"✅ Directorio logs/ ya existe")

def main():
    """Función principal"""
    print("🚀 Configuración Segura del Asistente Virtual SIMAP\n")
    
    # Verificar que estamos en el directorio correcto
    if not Path('app').exists() or not Path('config.ini').exists():
        print("❌ Este script debe ejecutarse desde la raíz del proyecto")
        sys.exit(1)
    
    # Crear directorio de logs
    crear_directorio_logs()
    
    # Limpiar config.ini
    if not limpiar_config_ini():
        print("❌ Error al limpiar config.ini")
        sys.exit(1)
    
    # Crear archivo .env
    if not crear_env_file():
        print("❌ Error al crear archivo .env")
        sys.exit(1)
    
    # Verificar seguridad
    if not verificar_seguridad():
        print("\n⚠️  Se encontraron problemas de seguridad. Revisa antes de hacer commit.")
    
    print("\n🎉 Configuración completada!")
    print("\n📋 Próximos pasos:")
    print("1. Revisa el archivo .env creado")
    print("2. Asegúrate de que .env está en .gitignore")
    print("3. NUNCA hagas commit de archivos con API keys reales")
    print("4. Usa 'git status' para verificar qué archivos se incluirán en el commit")

if __name__ == "__main__":
    main() 