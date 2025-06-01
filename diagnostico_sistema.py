#!/usr/bin/env python3
# diagnostico_sistema.py
"""
Script de Diagnóstico del Sistema - Asistente SIMAP
===================================================

Este script puede ejecutarse de forma independiente desde la línea de comandos
para diagnosticar el estado de la aplicación sin necesidad de que FastAPI esté ejecutándose.

Uso:
    python diagnostico_sistema.py
    python diagnostico_sistema.py --json
    python diagnostico_sistema.py --verbose
    python diagnostico_sistema.py --help

Funcionalidades:
- Verifica conexión con Qdrant
- Verifica base de datos relacional (MySQL/SQLite)
- Verifica conexión con OpenAI
- Verifica archivos críticos del sistema
- Detecta entorno de ejecución (Windows/Docker)
- Verifica entorno virtual en Windows
- Lógica dual MySQL/SQLite con fallback automático
- Genera reporte detallado en consola
- Opción de generar salida en formato JSON

Autor: Sistema SIMAP
Fecha: 2025
"""

import os
import sys
import time
import argparse
import json
import traceback
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Agregar el directorio del proyecto al path para poder importar módulos
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    # Imports de la aplicación
    from dotenv import load_dotenv
    from qdrant_client import QdrantClient
    from qdrant_client.http.exceptions import UnexpectedResponse
    import sqlite3
    import pymysql
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_qdrant import Qdrant
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Configuración desde variables de entorno
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'fragment_store')
    MODEL_NAME = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Configuración de base de datos
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")
    DB_HOST = os.getenv("BD_SERVER", "localhost")
    DB_PORT = int(os.getenv("BD_PORT", 3306))
    DB_NAME = os.getenv("BD_NAME", "avsp")
    DB_USER = os.getenv("BD_USER", "root")
    DB_PASS = os.getenv("BD_PASSWD", "")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "BD_RELA/local_database.db")
    
except ImportError as e:
    print(f"❌ Error importando dependencias: {e}")
    print("Asegúrate de tener instaladas todas las dependencias.")
    print("Ejecuta: pip install -r requirements.txt")
    sys.exit(1)

class ColoresConsola:
    """Colores para output en consola"""
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    ROJO = '\033[91m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BLANCO = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class DiagnosticoSistema:
    """Clase principal para diagnóstico del sistema"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = datetime.now()
        self.resultados = {}
        self.errores = []
        self.advertencias = []
        self.execution_environment = self.detectar_entorno_ejecucion()
        
    def print_colored(self, texto: str, color: str = ColoresConsola.BLANCO):
        """Imprimir texto con color"""
        print(f"{color}{texto}{ColoresConsola.RESET}")
    
    def print_status(self, status: str, mensaje: str):
        """Imprimir status con formato"""
        if status == "OK":
            icon = "✅"
            color = ColoresConsola.VERDE
        elif status == "WARNING":
            icon = "⚠️ "
            color = ColoresConsola.AMARILLO
        else:  # ERROR
            icon = "❌"
            color = ColoresConsola.ROJO
            
        self.print_colored(f"{icon} {mensaje}", color)
    
    def detectar_entorno_ejecucion(self) -> Dict[str, Any]:
        """Detectar el entorno de ejecución (Windows/Docker/Linux)"""
        try:
            env_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_executable": sys.executable,
                "is_docker": False,
                "is_windows": False,
                "virtual_env_active": False,
                "virtual_env_name": None,
                "virtual_env_path": None
            }
            
            # Detectar si está corriendo en Docker
            docker_indicators = [
                os.path.exists("/.dockerenv"),
                os.path.exists("/proc/1/cgroup") and any("docker" in line for line in open("/proc/1/cgroup", "r", errors="ignore")),
                os.getenv("DOCKER_CONTAINER") == "true"
            ]
            
            env_info["is_docker"] = any(docker_indicators)
            
            # Detectar Windows
            env_info["is_windows"] = platform.system().lower() == "windows"
            
            # Detectar entorno virtual
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                env_info["virtual_env_active"] = True
                env_info["virtual_env_path"] = sys.prefix
                
                # Obtener nombre del entorno virtual
                if env_info["is_windows"]:
                    # En Windows, el nombre suele estar en la ruta
                    venv_path = Path(sys.prefix)
                    env_info["virtual_env_name"] = venv_path.name
                else:
                    # En Linux/Docker
                    env_info["virtual_env_name"] = os.path.basename(sys.prefix)
            
            # Verificación específica para el entorno virtual "tot17" en Windows
            if env_info["is_windows"] and env_info["virtual_env_active"]:
                env_info["is_tot17_venv"] = env_info["virtual_env_name"].lower() == "tot17"
            else:
                env_info["is_tot17_venv"] = False
                
            return env_info
            
        except Exception as e:
            return {
                "platform": "unknown",
                "error": str(e),
                "is_docker": False,
                "is_windows": False,
                "virtual_env_active": False
            }

    def verificar_entorno_ejecucion(self) -> Dict[str, Any]:
        """Verificar y reportar el entorno de ejecución"""
        try:
            env = self.execution_environment
            
            # Determinar el estado y mensaje según el entorno
            if env["is_docker"]:
                status = "OK"
                message = "Ejecutándose en contenedor Docker"
                environment_type = "Docker Container"
                recommendations = [
                    "Verificar que requirements.txt esté actualizado",
                    "Monitorear recursos del contenedor",
                    "Verificar conectividad de red del contenedor"
                ]
            elif env["is_windows"]:
                if env["virtual_env_active"]:
                    if env.get("is_tot17_venv", False):
                        status = "OK"
                        message = "Ejecutándose en Windows con entorno virtual 'tot17' activo"
                        environment_type = "Windows + Virtual Environment (tot17)"
                        recommendations = [
                            "Entorno recomendado para desarrollo",
                            "Verificar que las dependencias estén actualizadas"
                        ]
                    else:
                        status = "WARNING"
                        message = f"Ejecutándose en Windows con entorno virtual '{env['virtual_env_name']}' (no es 'tot17')"
                        environment_type = f"Windows + Virtual Environment ({env['virtual_env_name']})"
                        recommendations = [
                            "Se recomienda usar el entorno virtual 'tot17'",
                            "Verificar que las dependencias sean compatibles"
                        ]
                else:
                    status = "WARNING"
                    message = "Ejecutándose en Windows SIN entorno virtual activo"
                    environment_type = "Windows (sin virtual environment)"
                    recommendations = [
                        "SE RECOMIENDA ACTIVAR EL ENTORNO VIRTUAL 'tot17'",
                        "Ejecutar: .\\tot17\\Scripts\\activate",
                        "Pueden ocurrir conflictos de dependencias sin venv"
                    ]
            else:
                # Linux u otro sistema
                status = "OK"
                message = f"Ejecutándose en {env['platform']}"
                environment_type = env['platform']
                recommendations = [
                    "Verificar que las dependencias del sistema estén instaladas"
                ]
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "environment_type": environment_type,
                    "platform": env["platform"],
                    "platform_version": env.get("platform_version", "unknown"),
                    "is_docker": env["is_docker"],
                    "is_windows": env["is_windows"],
                    "virtual_env_active": env["virtual_env_active"],
                    "virtual_env_name": env.get("virtual_env_name"),
                    "virtual_env_path": env.get("virtual_env_path"),
                    "python_executable": env["python_executable"],
                    "recommendations": recommendations
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando entorno de ejecución: {str(e)}",
                "error": str(e)
            }

    def verificar_python_entorno(self) -> Dict[str, Any]:
        """Verificar el entorno de Python"""
        try:
            return {
                "status": "OK",
                "message": "Entorno Python configurado correctamente",
                "details": {
                    "python_version": sys.version,
                    "python_path": sys.executable,
                    "working_directory": os.getcwd(),
                    "project_root": str(project_root),
                    "script_location": __file__
                }
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando entorno Python: {str(e)}",
                "error": str(e)
            }
    
    def verificar_archivos_criticos(self) -> Dict[str, Any]:
        """Verificar existencia de archivos críticos"""
        try:
            archivos_criticos = [
                "app/main.py",
                "app/core/dependencies.py", 
                "app/core/config.py",
                "app/api/endpoints.py",
                "BD_RELA/create_tables.py",
                "config.ini",
                "requirements.txt"
            ]
            
            archivos_encontrados = []
            archivos_faltantes = []
            detalles_archivos = {}
            
            for archivo in archivos_criticos:
                archivo_path = project_root / archivo
                if archivo_path.exists():
                    archivos_encontrados.append(archivo)
                    stat = archivo_path.stat()
                    detalles_archivos[archivo] = {
                        "exists": True,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    archivos_faltantes.append(archivo)
                    detalles_archivos[archivo] = {"exists": False}
            
            status = "OK" if len(archivos_faltantes) == 0 else "WARNING"
            
            return {
                "status": status,
                "message": f"Archivos críticos verificados: {len(archivos_encontrados)}/{len(archivos_criticos)} encontrados",
                "details": {
                    "archivos_encontrados": archivos_encontrados,
                    "archivos_faltantes": archivos_faltantes,
                    "detalles": detalles_archivos
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando archivos: {str(e)}",
                "error": str(e)
            }
    
    def verificar_variables_entorno(self) -> Dict[str, Any]:
        """Verificar variables de entorno críticas"""
        try:
            variables_requeridas = {
                "OPENAI_API_KEY": OPENAI_API_KEY,
                "QDRANT_URL": QDRANT_URL,
                "COLLECTION_NAME": COLLECTION_NAME,
                "MODEL_NAME": MODEL_NAME,
                "DB_TYPE": DB_TYPE
            }
            
            variables_configuradas = []
            variables_faltantes = []
            
            for var, valor in variables_requeridas.items():
                if valor:
                    variables_configuradas.append(var)
                else:
                    variables_faltantes.append(var)
            
            # Verificar archivo .env
            env_file = project_root / ".env"
            env_exists = env_file.exists()
            
            # Verificar config.ini
            config_file = project_root / "config.ini"
            config_exists = config_file.exists()
            
            status = "OK" if len(variables_faltantes) == 0 else "WARNING"
            
            return {
                "status": status,
                "message": f"Variables de entorno verificadas: {len(variables_configuradas)}/{len(variables_requeridas)} configuradas",
                "details": {
                    "variables_configuradas": variables_configuradas,
                    "variables_faltantes": variables_faltantes,
                    "env_file_exists": env_exists,
                    "config_file_exists": config_exists,
                    "openai_key_configured": bool(OPENAI_API_KEY),
                    "openai_key_preview": OPENAI_API_KEY[:10] + "..." if OPENAI_API_KEY else "No configurada"
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando variables de entorno: {str(e)}",
                "error": str(e)
            }
    
    def verificar_qdrant(self) -> Dict[str, Any]:
        """Verificar conexión con Qdrant"""
        try:
            self.print_colored("  Conectando con Qdrant...", ColoresConsola.CYAN)
            
            client = QdrantClient(url=QDRANT_URL)
            
            # Verificar conexión básica
            collections = client.get_collections()
            
            # Verificar colección específica
            collection_exists = False
            collection_info = None
            try:
                collection_data = client.get_collection(COLLECTION_NAME)
                collection_exists = True
                collection_info = {
                    "vectors_count": collection_data.vectors_count,
                    "status": str(collection_data.status)
                }
            except Exception:
                pass
            
            # Intentar una consulta de prueba si la colección existe
            query_test_result = None
            if collection_exists and OPENAI_API_KEY:
                try:
                    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
                    vector_store = Qdrant(
                        client=client,
                        collection_name=COLLECTION_NAME,
                        embeddings=embeddings
                    )
                    
                    start_time = time.time()
                    results = vector_store.similarity_search("consulta de prueba", k=1)
                    query_time = (time.time() - start_time) * 1000
                    
                    query_test_result = {
                        "success": True,
                        "results_count": len(results),
                        "response_time_ms": round(query_time, 2)
                    }
                except Exception as e:
                    query_test_result = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "status": "OK",
                "message": "Qdrant conectado correctamente",
                "details": {
                    "url": QDRANT_URL,
                    "total_collections": len(collections.collections),
                    "target_collection": COLLECTION_NAME,
                    "collection_exists": collection_exists,
                    "collection_info": collection_info,
                    "query_test": query_test_result
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con Qdrant: {str(e)}",
                "error": str(e),
                "details": {
                    "url": QDRANT_URL,
                    "target_collection": COLLECTION_NAME
                }
            }
    
    def verificar_base_datos_dual(self) -> Dict[str, Any]:
        """Verificar conexión dual MySQL/SQLite con fallback automático"""
        try:
            mysql_result = None
            sqlite_result = None
            active_connection = None
            
            # Primero intentar MySQL
            try:
                self.print_colored("  Intentando conexión con MySQL...", ColoresConsola.CYAN)
                mysql_result = self._verificar_mysql()
                if mysql_result["status"] == "OK":
                    active_connection = "MySQL"
            except Exception as e:
                mysql_result = {
                    "status": "ERROR",
                    "message": f"MySQL no disponible: {str(e)}",
                    "error": str(e)
                }
            
            # Si MySQL falla, intentar SQLite
            if not active_connection:
                try:
                    self.print_colored("  MySQL falló, intentando SQLite...", ColoresConsola.AMARILLO)
                    sqlite_result = self._verificar_sqlite()
                    if sqlite_result["status"] == "OK":
                        active_connection = "SQLite"
                except Exception as e:
                    sqlite_result = {
                        "status": "ERROR",
                        "message": f"SQLite no disponible: {str(e)}",
                        "error": str(e)
                    }
            
            # Determinar el estado final
            if active_connection == "MySQL":
                status = "OK"
                message = "Conectado a MySQL (base de datos principal)"
                primary_db = mysql_result
            elif active_connection == "SQLite":
                status = "WARNING"
                message = "Conectado a SQLite (MySQL desactivado/no disponible - fallback activo)"
                primary_db = sqlite_result
            else:
                status = "ERROR"
                message = "No se pudo conectar ni a MySQL ni a SQLite"
                primary_db = None
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "active_connection": active_connection,
                    "dual_mode": True,
                    "mysql_status": mysql_result["status"] if mysql_result else "NOT_ATTEMPTED",
                    "sqlite_status": sqlite_result["status"] if sqlite_result else "NOT_ATTEMPTED",
                    "mysql_details": mysql_result if mysql_result else None,
                    "sqlite_details": sqlite_result if sqlite_result else None,
                    "primary_database": primary_db["details"] if primary_db and "details" in primary_db else None,
                    "fallback_explanation": {
                        "strategy": "MySQL primary, SQLite fallback",
                        "current_mode": active_connection,
                        "recommendation": "MySQL recomendado para producción" if active_connection == "SQLite" else "Configuración óptima"
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error en verificación dual de base de datos: {str(e)}",
                "error": str(e)
            }
    
    def _verificar_mysql(self) -> Dict[str, Any]:
        """Verificar MySQL específicamente"""
        try:
            connection = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                cursor.execute("SHOW TABLES")
                tables = [list(table.values())[0] for table in cursor.fetchall()]
                
                # Contar registros en tablas principales
                table_counts = {}
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        result = cursor.fetchone()
                        table_counts[table] = result['count']
                    except Exception:
                        table_counts[table] = "Error"
            
            connection.close()
            
            return {
                "status": "OK",
                "message": "MySQL conectado correctamente",
                "details": {
                    "database_type": "MySQL",
                    "host": f"{DB_HOST}:{DB_PORT}",
                    "database": DB_NAME,
                    "user": DB_USER,
                    "tables_count": len(tables),
                    "tables": tables,
                    "table_record_counts": table_counts
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con MySQL: {str(e)}",
                "error": str(e)
            }
    
    def _verificar_sqlite(self) -> Dict[str, Any]:
        """Verificar SQLite específicamente"""
        try:
            sqlite_path = project_root / SQLITE_PATH
            
            if not sqlite_path.exists():
                return {
                    "status": "ERROR",
                    "message": f"Archivo SQLite no encontrado: {sqlite_path}",
                    "error": "File not found"
                }
            
            connection = sqlite3.connect(str(sqlite_path))
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            
            cursor.execute("SELECT 1 as test")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Contar registros en tablas
            table_counts = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_counts[table] = count
                except Exception:
                    table_counts[table] = "Error"
            
            connection.close()
            
            return {
                "status": "OK",
                "message": "SQLite conectado correctamente",
                "details": {
                    "database_type": "SQLite",
                    "file_path": str(sqlite_path),
                    "file_size_mb": round(sqlite_path.stat().st_size / (1024*1024), 2),
                    "tables_count": len(tables),
                    "tables": tables,
                    "table_record_counts": table_counts
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con SQLite: {str(e)}",
                "error": str(e)
            }
    
    def verificar_openai(self) -> Dict[str, Any]:
        """Verificar conexión con OpenAI"""
        try:
            if not OPENAI_API_KEY:
                return {
                    "status": "ERROR",
                    "message": "API Key de OpenAI no configurada",
                    "error": "Missing API key"
                }
            
            self.print_colored("  Verificando OpenAI...", ColoresConsola.CYAN)
            
            # Probar embeddings
            embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
            start_time = time.time()
            test_embedding = embeddings.embed_query("texto de prueba")
            embedding_time = (time.time() - start_time) * 1000
            
            # Probar LLM
            llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
            start_time = time.time()
            test_response = llm.invoke("Responde solo 'OK' para confirmar funcionamiento")
            llm_time = (time.time() - start_time) * 1000
            
            return {
                "status": "OK",
                "message": "OpenAI conectado y funcionando",
                "details": {
                    "api_key_configured": True,
                    "api_key_preview": OPENAI_API_KEY[:10] + "...",
                    "model": MODEL_NAME,
                    "embedding_test": {
                        "success": True,
                        "vector_size": len(test_embedding),
                        "response_time_ms": round(embedding_time, 2)
                    },
                    "llm_test": {
                        "success": True,
                        "response": test_response.content[:50] + "..." if len(test_response.content) > 50 else test_response.content,
                        "response_time_ms": round(llm_time, 2)
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error con OpenAI: {str(e)}",
                "error": str(e),
                "details": {
                    "api_key_configured": bool(OPENAI_API_KEY),
                    "model": MODEL_NAME
                }
            }
    
    def ejecutar_diagnostico_completo(self) -> Dict[str, Any]:
        """Ejecutar diagnóstico completo del sistema"""
        
        self.print_colored("🔍 DIAGNÓSTICO DEL SISTEMA - ASISTENTE SIMAP", ColoresConsola.BOLD + ColoresConsola.AZUL)
        self.print_colored("=" * 60, ColoresConsola.AZUL)
        
        verificaciones = {
            "entorno_ejecucion": ("🖥️ Entorno de Ejecución", self.verificar_entorno_ejecucion),
            "python_entorno": ("🐍 Python y Entorno", self.verificar_python_entorno),
            "variables_entorno": ("⚙️  Variables de Entorno", self.verificar_variables_entorno),
            "archivos_criticos": ("📁 Archivos Críticos", self.verificar_archivos_criticos),
            "qdrant": ("🔍 Qdrant (Base Vectorial)", self.verificar_qdrant),
            "base_datos_dual": ("🗄️  Base de Datos (MySQL/SQLite)", self.verificar_base_datos_dual),
            "openai": ("🤖 OpenAI", self.verificar_openai)
        }
        
        resultados = {}
        estado_general = "OK"
        
        for clave, (descripcion, funcion) in verificaciones.items():
            self.print_colored(f"\n{descripcion}:", ColoresConsola.BOLD)
            
            try:
                resultado = funcion()
                resultados[clave] = resultado
                
                self.print_status(resultado["status"], resultado["message"])
                
                if self.verbose and "details" in resultado:
                    self.print_colored("  Detalles:", ColoresConsola.CYAN)
                    for key, value in resultado["details"].items():
                        if isinstance(value, dict):
                            self.print_colored(f"    {key.replace('_', ' ').title()}:", ColoresConsola.BLANCO)
                            for k, v in value.items():
                                if isinstance(v, list):
                                    v_str = ', '.join(map(str, v)) if v else "None"
                                    print(f"      {k.replace('_', ' ').title()}: {v_str}")
                                else:
                                    print(f"      {k.replace('_', ' ').title()}: {v}")
                        elif isinstance(value, list):
                            if value and isinstance(value[0], str):
                                self.print_colored(f"    {key.replace('_', ' ').title()}:", ColoresConsola.BLANCO)
                                for item in value:
                                    print(f"      • {item}")
                            else:
                                self.print_colored(f"    {key.replace('_', ' ').title()}: {', '.join(map(str, value)) if value else 'None'}", ColoresConsola.BLANCO)
                        else:
                            self.print_colored(f"    {key.replace('_', ' ').title()}: {value}", ColoresConsola.BLANCO)
                
                if resultado["status"] == "ERROR":
                    estado_general = "ERROR"
                    self.errores.append(f"{descripcion}: {resultado['message']}")
                elif resultado["status"] == "WARNING" and estado_general == "OK":
                    estado_general = "WARNING"
                    self.advertencias.append(f"{descripcion}: {resultado['message']}")
                    
            except Exception as e:
                error_msg = f"Error ejecutando verificación de {descripcion}: {str(e)}"
                self.print_status("ERROR", error_msg)
                
                resultados[clave] = {
                    "status": "ERROR",
                    "message": error_msg,
                    "error": str(e)
                }
                
                estado_general = "ERROR"
                self.errores.append(error_msg)
        
        tiempo_ejecucion = (datetime.now() - self.start_time).total_seconds()
        
        # Resumen final
        self.print_colored("\n" + "=" * 60, ColoresConsola.AZUL)
        self.print_colored("📋 RESUMEN DEL DIAGNÓSTICO", ColoresConsola.BOLD + ColoresConsola.AZUL)
        self.print_colored("=" * 60, ColoresConsola.AZUL)
        
        self.print_status(estado_general, f"Estado General del Sistema: {estado_general}")
        
        exitosas = sum(1 for r in resultados.values() if r["status"] == "OK")
        advertencias = sum(1 for r in resultados.values() if r["status"] == "WARNING")
        errores = sum(1 for r in resultados.values() if r["status"] == "ERROR")
        
        print(f"✅ Verificaciones exitosas: {exitosas}")
        print(f"⚠️  Advertencias: {advertencias}")
        print(f"❌ Errores: {errores}")
        print(f"⏱️  Tiempo de ejecución: {tiempo_ejecucion:.2f} segundos")
        
        # Mostrar información del entorno
        env = self.execution_environment
        if env.get("is_docker"):
            self.print_colored("\n🐳 ENTORNO: Docker Container", ColoresConsola.CYAN + ColoresConsola.BOLD)
        elif env.get("is_windows"):
            if env.get("virtual_env_active"):
                venv_name = env.get("virtual_env_name", "unknown")
                if venv_name.lower() == "tot17":
                    self.print_colored(f"\n🖥️ ENTORNO: Windows + Virtual Environment ({venv_name}) ✅", ColoresConsola.VERDE + ColoresConsola.BOLD)
                else:
                    self.print_colored(f"\n🖥️ ENTORNO: Windows + Virtual Environment ({venv_name}) ⚠️", ColoresConsola.AMARILLO + ColoresConsola.BOLD)
            else:
                self.print_colored("\n🖥️ ENTORNO: Windows (sin virtual environment) ⚠️", ColoresConsola.AMARILLO + ColoresConsola.BOLD)
        else:
            self.print_colored(f"\n🐧 ENTORNO: {env.get('platform', 'Linux')}", ColoresConsola.AZUL + ColoresConsola.BOLD)
        
        if self.errores:
            self.print_colored("\n🚨 ERRORES ENCONTRADOS:", ColoresConsola.ROJO + ColoresConsola.BOLD)
            for error in self.errores:
                self.print_colored(f"  • {error}", ColoresConsola.ROJO)
        
        if self.advertencias:
            self.print_colored("\n⚠️  ADVERTENCIAS:", ColoresConsola.AMARILLO + ColoresConsola.BOLD)
            for advertencia in self.advertencias:
                self.print_colored(f"  • {advertencia}", ColoresConsola.AMARILLO)
        
        if estado_general == "OK":
            self.print_colored("\n🎉 ¡Sistema funcionando correctamente!", ColoresConsola.VERDE + ColoresConsola.BOLD)
        elif estado_general == "WARNING":
            self.print_colored("\n⚠️  Sistema funcionando con advertencias", ColoresConsola.AMARILLO + ColoresConsola.BOLD)
        else:
            self.print_colored("\n🚨 Sistema con problemas críticos", ColoresConsola.ROJO + ColoresConsola.BOLD)
        
        # Generar resultado estructurado
        resultado_final = {
            "resumen": {
                "estado_general": estado_general,
                "timestamp": datetime.now().isoformat(),
                "tiempo_ejecucion_segundos": round(tiempo_ejecucion, 2),
                "total_verificaciones": len(verificaciones),
                "verificaciones_exitosas": exitosas,
                "advertencias": advertencias,
                "errores": errores,
                "mensajes_error": self.errores,
                "mensajes_advertencia": self.advertencias
            },
            "resultados_detallados": resultados,
            "informacion_sistema": {
                "execution_environment": self.execution_environment,
                "database_type": DB_TYPE,
                "qdrant_url": QDRANT_URL,
                "openai_model": MODEL_NAME,
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "script_path": __file__
            }
        }
        
        return resultado_final

def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Diagnóstico completo del Sistema SIMAP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python diagnostico_sistema.py              # Diagnóstico básico
  python diagnostico_sistema.py --verbose    # Diagnóstico detallado
  python diagnostico_sistema.py --json       # Salida en formato JSON
  python diagnostico_sistema.py --json --verbose > diagnostico.json  # Guardar JSON
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar información detallada de cada verificación"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Generar salida en formato JSON"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Archivo donde guardar el resultado JSON"
    )
    
    args = parser.parse_args()
    
    try:
        diagnostico = DiagnosticoSistema(verbose=args.verbose)
        resultado = diagnostico.ejecutar_diagnostico_completo()
        
        if args.json:
            json_output = json.dumps(resultado, indent=2, ensure_ascii=False)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"\n📄 Resultado guardado en: {args.output}")
            else:
                print("\n" + "="*60)
                print("JSON OUTPUT:")
                print("="*60)
                print(json_output)
        
        # Código de salida basado en el estado
        if resultado["resumen"]["estado_general"] == "OK":
            sys.exit(0)
        elif resultado["resumen"]["estado_general"] == "WARNING":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Diagnóstico interrumpido por el usuario")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n❌ Error crítico ejecutando diagnóstico: {str(e)}")
        if args.verbose:
            print("\nTraceback completo:")
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 