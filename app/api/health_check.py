# app/api/health_check.py
import os
import sys
import time
import traceback
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Imports para FastAPI
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

# Imports para conexiones
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import pymysql
import sqlite3

# Imports de la aplicación
from app.core.dependencies import get_embeddings, get_qdrant_client, get_vector_store, get_llm
from app.core.config import qdrant_url, collection_name_fragmento, openai_api_key
from app.core.logging_config import get_logger

# Imports para Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

# Imports para base de datos
from dotenv import load_dotenv

logger = get_logger()

class HealthChecker:
    """Clase para realizar diagnósticos completos del sistema"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.load_env_config()
        self.execution_environment = self.detect_execution_environment()
    
    def load_env_config(self):
        """Cargar configuración de variables de entorno"""
        load_dotenv()
        self.db_type = os.getenv("DB_TYPE", "sqlite")
        self.db_host = os.getenv("BD_SERVER", "localhost")
        self.db_port = int(os.getenv("BD_PORT", 3306))
        self.db_name = os.getenv("BD_NAME", "avsp")
        self.db_user = os.getenv("BD_USER", "root")
        self.db_pass = os.getenv("BD_PASSWD", "")
        self.sqlite_path = os.getenv("SQLITE_PATH", "BD_RELA/local_database.db")

    def detect_execution_environment(self) -> Dict[str, Any]:
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

    def check_execution_environment(self) -> Dict[str, Any]:
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

    def check_uvicorn_status(self) -> Dict[str, Any]:
        """Verificar que Uvicorn está funcionando"""
        try:
            # Si llegamos aquí, Uvicorn está funcionando porque está procesando esta request
            import uvicorn
            
            # Intentar importar psutil para información adicional
            try:
                import psutil
                has_psutil = True
            except ImportError:
                has_psutil = False
            
            if has_psutil:
                current_pid = os.getpid()
                current_process = psutil.Process(current_pid)
                
                try:
                    parent_process = current_process.parent()
                    parent_info = {
                        "parent_pid": parent_process.pid,
                        "parent_process_name": parent_process.name()
                    }
                except Exception:
                    parent_info = {
                        "parent_pid": None,
                        "parent_process_name": None
                    }
                
                # Información del proceso actual
                process_info = {
                    "current_pid": current_pid,
                    "current_process_name": current_process.name(),
                    "memory_usage_mb": round(current_process.memory_info().rss / 1024 / 1024, 2),
                    "cpu_percent": round(current_process.cpu_percent(), 2),
                    "create_time": datetime.fromtimestamp(current_process.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                    **parent_info
                }
                
                ports_listening = self._get_listening_ports()
            else:
                process_info = {
                    "current_pid": os.getpid(),
                    "psutil_available": False,
                    "note": "Instalar psutil para información detallada del proceso"
                }
                ports_listening = []
            
            return {
                "status": "OK",
                "message": "Uvicorn está ejecutándose correctamente (confirmado: puede procesar esta request)",
                "details": {
                    "uvicorn_version": getattr(uvicorn, "__version__", "unknown"),
                    "process_info": process_info,
                    "working_directory": os.getcwd(),
                    "environment_type": self.execution_environment.get("environment_type", "unknown"),
                    "explanation": "Si este endpoint responde, significa que Uvicorn está activo y procesando requests HTTP",
                    "server_status": "ACTIVE - Procesando requests",
                    "ports_listening": ports_listening,
                    "logical_proof": "La respuesta a esta request confirma que Uvicorn está funcionando"
                }
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando Uvicorn: {str(e)}",
                "error": str(e),
                "details": {
                    "explanation": "Error interno al verificar el estado del servidor"
                }
            }

    def _get_listening_ports(self) -> List[int]:
        """Obtener puertos en los que está escuchando el proceso actual"""
        try:
            import psutil
            current_process = psutil.Process(os.getpid())
            listening_ports = []
            
            # Obtener conexiones del proceso actual
            connections = current_process.connections(kind='inet')
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    listening_ports.append(conn.laddr.port)
            
            return sorted(list(set(listening_ports)))
        except Exception:
            return []

    def check_qdrant_connection(self) -> Dict[str, Any]:
        """Verificar conexión con Qdrant"""
        try:
            client = QdrantClient(url=qdrant_url)
            
            # Verificar que el servicio responde
            collections = client.get_collections()
            
            # Verificar la colección específica
            try:
                collection_info = client.get_collection(collection_name_fragmento)
                collection_exists = True
                collection_details = {
                    "vectors_count": collection_info.vectors_count,
                    "status": collection_info.status.value if hasattr(collection_info.status, 'value') else str(collection_info.status)
                }
            except Exception:
                collection_exists = False
                collection_details = None
            
            return {
                "status": "OK",
                "message": "Qdrant está funcionando correctamente",
                "details": {
                    "url": qdrant_url,
                    "total_collections": len(collections.collections),
                    "target_collection": collection_name_fragmento,
                    "collection_exists": collection_exists,
                    "collection_details": collection_details
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con Qdrant: {str(e)}",
                "error": str(e),
                "details": {
                    "url": qdrant_url,
                    "target_collection": collection_name_fragmento
                }
            }

    def check_qdrant_vectorial_db(self) -> Dict[str, Any]:
        """Verificar base de datos vectorial de Qdrant con una consulta de prueba"""
        try:
            vector_store = get_vector_store()
            
            # Realizar una consulta de prueba
            test_query = "consulta de prueba para verificar funcionamiento"
            start_time = time.time()
            results = vector_store.similarity_search(test_query, k=3)
            response_time = (time.time() - start_time) * 1000  # en ms
            
            return {
                "status": "OK",
                "message": "Base de datos vectorial responde correctamente",
                "details": {
                    "query_executed": test_query,
                    "results_found": len(results),
                    "response_time_ms": round(response_time, 2),
                    "sample_results": [{"content": r.page_content[:100] + "..." if len(r.page_content) > 100 else r.page_content} for r in results[:2]]
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error en base de datos vectorial: {str(e)}",
                "error": str(e)
            }

    def check_database_dual_connection(self) -> Dict[str, Any]:
        """Verificar conexión dual MySQL/SQLite con fallback automático"""
        try:
            mysql_result = None
            sqlite_result = None
            active_connection = None
            
            # Primero intentar MySQL
            try:
                mysql_result = self.check_mysql_connection()
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
                    sqlite_result = self.check_sqlite_connection()
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

    def check_mysql_connection(self) -> Dict[str, Any]:
        """Verificar conexión MySQL"""
        try:
            connection = pymysql.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_pass,
                database=self.db_name,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                # Verificar tablas existentes
                cursor.execute("SHOW TABLES")
                tables = [table['Tables_in_' + self.db_name] for table in cursor.fetchall()]
                
            connection.close()
            
            return {
                "status": "OK",
                "message": "MySQL conectado correctamente",
                "details": {
                    "host": f"{self.db_host}:{self.db_port}",
                    "database": self.db_name,
                    "user": self.db_user,
                    "tables_count": len(tables),
                    "tables": tables
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con MySQL: {str(e)}",
                "error": str(e),
                "details": {
                    "host": f"{self.db_host}:{self.db_port}",
                    "database": self.db_name,
                    "user": self.db_user
                }
            }

    def check_sqlite_connection(self) -> Dict[str, Any]:
        """Verificar conexión SQLite"""
        try:
            if not os.path.exists(self.sqlite_path):
                return {
                    "status": "ERROR",
                    "message": f"Archivo SQLite no encontrado: {self.sqlite_path}",
                    "error": "File not found"
                }
            
            connection = sqlite3.connect(self.sqlite_path)
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            
            # Verificar que la conexión funciona
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            # Obtener tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            connection.close()
            
            return {
                "status": "OK",
                "message": "SQLite conectado correctamente",
                "details": {
                    "file_path": self.sqlite_path,
                    "file_size_mb": round(os.path.getsize(self.sqlite_path) / (1024*1024), 2),
                    "tables_count": len(tables),
                    "tables": tables
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error conectando con SQLite: {str(e)}",
                "error": str(e),
                "details": {
                    "file_path": self.sqlite_path
                }
            }

    def check_database_tables(self) -> Dict[str, Any]:
        """Verificar que todas las tablas del sistema existen y funcionan usando la conexión activa"""
        try:
            expected_tables = ['usuarios', 'prompts', 'consultas', 'feedback_respuesta', 'log_batch_bdv', 'log_arranque_app']
            
            # Usar la verificación dual para determinar qué BD está activa
            dual_result = self.check_database_dual_connection()
            if dual_result["status"] == "ERROR":
                return dual_result
            
            active_connection = dual_result["details"]["active_connection"]
            
            if active_connection == "MySQL":
                db_result = self.check_mysql_connection()
            else:  # SQLite
                db_result = self.check_sqlite_connection()
            
            if db_result["status"] == "ERROR":
                return db_result
            
            existing_tables = db_result["details"]["tables"]
            missing_tables = [table for table in expected_tables if table not in existing_tables]
            extra_tables = [table for table in existing_tables if table not in expected_tables]
            
            # Verificar que las tablas principales tienen datos
            table_stats = {}
            
            if active_connection == "MySQL":
                connection = pymysql.connect(
                    host=self.db_host, port=self.db_port, user=self.db_user,
                    password=self.db_pass, database=self.db_name, charset='utf8mb4'
                )
                cursor = connection.cursor()
                
                for table in existing_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_stats[table] = count
                    except Exception as e:
                        table_stats[table] = f"Error: {str(e)}"
                
                connection.close()
                
            else:  # SQLite
                connection = sqlite3.connect(self.sqlite_path)
                cursor = connection.cursor()
                
                for table in existing_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_stats[table] = count
                    except Exception as e:
                        table_stats[table] = f"Error: {str(e)}"
                
                connection.close()
            
            status = "OK" if len(missing_tables) == 0 else "WARNING"
            message = "Todas las tablas están presentes" if len(missing_tables) == 0 else f"Faltan {len(missing_tables)} tablas"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "active_database": active_connection,
                    "database_type": active_connection,
                    "expected_tables": expected_tables,
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "extra_tables": extra_tables,
                    "table_record_counts": table_stats
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando tablas: {str(e)}",
                "error": str(e)
            }

    def check_openai_connection(self) -> Dict[str, Any]:
        """Verificar conexión con OpenAI"""
        try:
            embeddings = get_embeddings()
            llm = get_llm()
            
            # Probar embeddings
            start_time = time.time()
            test_embedding = embeddings.embed_query("texto de prueba")
            embedding_time = (time.time() - start_time) * 1000
            
            # Probar LLM
            start_time = time.time()
            test_response = llm.invoke("Responde solo 'OK' para confirmar que funciona")
            llm_time = (time.time() - start_time) * 1000
            
            return {
                "status": "OK",
                "message": "OpenAI conectado y funcionando",
                "details": {
                    "api_key_configured": bool(openai_api_key),
                    "api_key_prefix": openai_api_key[:10] + "..." if openai_api_key else "Not configured",
                    "embedding_test": {
                        "success": True,
                        "vector_size": len(test_embedding),
                        "response_time_ms": round(embedding_time, 2)
                    },
                    "llm_test": {
                        "success": True,
                        "response": test_response.content[:100],
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
                    "api_key_configured": bool(openai_api_key),
                    "api_key_prefix": openai_api_key[:10] + "..." if openai_api_key else "Not configured"
                }
            }

    def check_critical_scripts(self) -> Dict[str, Any]:
        """Verificar scripts críticos de la aplicación"""
        try:
            critical_files = [
                "app/main.py",
                "app/core/dependencies.py",
                "app/core/config.py",
                "app/api/endpoints.py",
                "BD_RELA/create_tables.py",
                "config.ini"
            ]
            
            file_status = {}
            
            for file_path in critical_files:
                if os.path.exists(file_path):
                    file_stats = os.stat(file_path)
                    file_status[file_path] = {
                        "exists": True,
                        "size_kb": round(file_stats.st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    file_status[file_path] = {
                        "exists": False,
                        "error": "File not found"
                    }
            
            missing_files = [f for f, status in file_status.items() if not status["exists"]]
            
            return {
                "status": "OK" if len(missing_files) == 0 else "WARNING",
                "message": f"Scripts críticos verificados. {len(missing_files)} archivos faltantes." if missing_files else "Todos los scripts críticos están presentes",
                "details": {
                    "total_files_checked": len(critical_files),
                    "missing_files": missing_files,
                    "file_status": file_status
                }
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error verificando scripts: {str(e)}",
                "error": str(e)
            }

    def run_full_diagnosis(self) -> Dict[str, Any]:
        """Ejecutar diagnóstico completo"""
        logger.info("Iniciando diagnóstico completo del sistema")
        
        checks = {
            "execution_environment": self.check_execution_environment,
            "uvicorn": self.check_uvicorn_status,
            "qdrant_connection": self.check_qdrant_connection,
            "qdrant_vectorial_db": self.check_qdrant_vectorial_db,
            "database_dual_connection": self.check_database_dual_connection,
            "database_tables": self.check_database_tables,
            "openai_connection": self.check_openai_connection,
            "critical_scripts": self.check_critical_scripts
        }
        
        results = {}
        overall_status = "OK"
        errors = []
        warnings = []
        
        for check_name, check_function in checks.items():
            try:
                logger.info(f"Ejecutando verificación: {check_name}")
                result = check_function()
                results[check_name] = result
                
                if result["status"] == "ERROR":
                    overall_status = "ERROR"
                    errors.append(f"{check_name}: {result['message']}")
                elif result["status"] == "WARNING":
                    if overall_status == "OK":
                        overall_status = "WARNING"
                    warnings.append(f"{check_name}: {result['message']}")
                    
            except Exception as e:
                logger.error(f"Error en verificación {check_name}: {str(e)}")
                results[check_name] = {
                    "status": "ERROR",
                    "message": f"Error ejecutando verificación: {str(e)}",
                    "error": str(e)
                }
                overall_status = "ERROR"
                errors.append(f"{check_name}: Error ejecutando verificación")
        
        execution_time = (datetime.now() - self.start_time).total_seconds()
        
        summary = {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "execution_time_seconds": round(execution_time, 2),
            "total_checks": len(checks),
            "successful_checks": sum(1 for r in results.values() if r["status"] == "OK"),
            "warnings": len(warnings),
            "errors": len(errors),
            "error_messages": errors,
            "warning_messages": warnings,
            "system_info": {
                "execution_environment": self.execution_environment,
                "database_type": self.db_type,
                "qdrant_url": qdrant_url,
                "working_directory": os.getcwd(),
                "python_version": sys.version
            }
        }
        
        return {
            "summary": summary,
            "detailed_results": results
        }

# Funciones para el endpoint de FastAPI
def get_health_check_html(diagnosis_result: Dict[str, Any]) -> str:
    """Generar HTML para mostrar el diagnóstico"""
    
    summary = diagnosis_result["summary"]
    results = diagnosis_result["detailed_results"]
    
    # Determinar color del status general
    status_color = {
        "OK": "#28a745",      # Verde
        "WARNING": "#ffc107", # Amarillo
        "ERROR": "#dc3545"    # Rojo
    }.get(summary["overall_status"], "#6c757d")
    
    # Generar HTML de resultados detallados
    detailed_html = ""
    for check_name, result in results.items():
        status_icon = {
            "OK": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(result["status"], "❓")
        
        # Nombres más amigables para el frontend
        friendly_names = {
            "execution_environment": "🖥️ Entorno de Ejecución",
            "uvicorn": "🚀 Servidor Web (Uvicorn)",
            "qdrant_connection": "🔍 Conexión Qdrant",
            "qdrant_vectorial_db": "📊 Base de Datos Vectorial",
            "database_dual_connection": "🗄️ Base de Datos (MySQL/SQLite)",
            "database_tables": "📋 Tablas del Sistema",
            "openai_connection": "🤖 Conexión OpenAI",
            "critical_scripts": "📁 Scripts Críticos"
        }
        
        display_name = friendly_names.get(check_name, check_name.replace('_', ' ').title())
        
        # Explicación especial para Uvicorn
        explanation_note = ""
        if check_name == "uvicorn" and result["status"] == "OK":
            explanation_note = """
            <div class="alert alert-info mt-2">
                <small><strong>📝 Nota:</strong> Si puedes ver esta página, significa que Uvicorn está funcionando correctamente. 
                El servidor web está activo y procesando tu request HTTP en este momento.</small>
            </div>
            """
        
        details_html = ""
        if "details" in result:
            details_html = "<ul>"
            for key, value in result["details"].items():
                if isinstance(value, dict):
                    details_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong>"
                    details_html += "<ul>"
                    for k, v in value.items():
                        if isinstance(v, list):
                            v_str = ', '.join(map(str, v)) if v else "None"
                        else:
                            v_str = str(v)
                        details_html += f"<li>{k.replace('_', ' ').title()}: {v_str}</li>"
                    details_html += "</ul></li>"
                elif isinstance(value, list):
                    if value:
                        if isinstance(value[0], str):
                            details_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong>"
                            details_html += "<ul>"
                            for item in value:
                                details_html += f"<li>{item}</li>"
                            details_html += "</ul></li>"
                        else:
                            details_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {', '.join(map(str, value))}</li>"
                    else:
                        details_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> None</li>"
                else:
                    details_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
            details_html += "</ul>"
        
        # Clase CSS especial para base de datos dual
        card_class = "card mb-3"
        if check_name == "database_dual_connection" and result["status"] == "WARNING":
            card_class += " border-warning"
        elif check_name == "execution_environment" and result["status"] == "WARNING":
            card_class += " border-warning"
        
        detailed_html += f"""
        <div class="{card_class}">
            <div class="card-header">
                <h5>{status_icon} {display_name}</h5>
            </div>
            <div class="card-body">
                <p><strong>Status:</strong> <span class="badge badge-{result['status'].lower()}">{result['status']}</span></p>
                <p><strong>Mensaje:</strong> {result['message']}</p>
                {explanation_note}
                {details_html}
            </div>
        </div>
        """
    
    # Agregar información específica del entorno
    env_info = summary.get("system_info", {}).get("execution_environment", {})
    env_summary = ""
    if env_info:
        if env_info.get("is_docker"):
            env_summary = "🐳 <strong>Docker Container</strong>"
        elif env_info.get("is_windows"):
            if env_info.get("virtual_env_active"):
                venv_name = env_info.get("virtual_env_name", "unknown")
                if venv_name.lower() == "tot17":
                    env_summary = f"🖥️ <strong>Windows + Virtual Environment ({venv_name})</strong> ✅"
                else:
                    env_summary = f"🖥️ <strong>Windows + Virtual Environment ({venv_name})</strong> ⚠️"
            else:
                env_summary = "🖥️ <strong>Windows (sin virtual environment)</strong> ⚠️"
        else:
            env_summary = f"🐧 <strong>{env_info.get('platform', 'Linux')}</strong>"
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Diagnóstico del Sistema - Asistente SIMAP</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .status-ok {{ background-color: #d4edda; border-color: #c3e6cb; }}
            .status-warning {{ background-color: #fff3cd; border-color: #ffeaa7; }}
            .status-error {{ background-color: #f8d7da; border-color: #f5c6cb; }}
            .badge-ok {{ background-color: #28a745; }}
            .badge-warning {{ background-color: #ffc107; color: #212529; }}
            .badge-error {{ background-color: #dc3545; }}
            .card {{ box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); }}
            .refresh-btn {{ 
                position: fixed; 
                bottom: 20px; 
                right: 20px; 
                z-index: 1000;
            }}
            .environment-info {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .border-warning {{
                border-left: 4px solid #ffc107 !important;
            }}
        </style>
    </head>
    <body class="bg-light">
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <div class="card status-{summary['overall_status'].lower()}">
                        <div class="card-header">
                            <h1 class="h3">🔍 Diagnóstico del Sistema - Asistente SIMAP</h1>
                            <p class="mb-0">Estado General: <strong style="color: {status_color};">{summary['overall_status']}</strong></p>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="text-center">
                                        <h4 class="text-success">{summary['successful_checks']}</h4>
                                        <small>Verificaciones Exitosas</small>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-center">
                                        <h4 class="text-warning">{summary['warnings']}</h4>
                                        <small>Advertencias</small>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-center">
                                        <h4 class="text-danger">{summary['errors']}</h4>
                                        <small>Errores</small>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-center">
                                        <h4 class="text-info">{summary['execution_time_seconds']}s</h4>
                                        <small>Tiempo de Ejecución</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {"<div class='environment-info'><h5>🖥️ Entorno de Ejecución</h5><p class='mb-0'>" + env_summary + "</p></div>" if env_summary else ""}
                    
                    <h2 class="mt-4 mb-3">📋 Resultados Detallados</h2>
                    {detailed_html}
                    
                    <div class="card mt-4">
                        <div class="card-header">
                            <h5>ℹ️ Información del Sistema</h5>
                        </div>
                        <div class="card-body">
                            <ul>
                                <li><strong>Tipo de Base de Datos:</strong> {summary['system_info']['database_type']}</li>
                                <li><strong>URL de Qdrant:</strong> {summary['system_info']['qdrant_url']}</li>
                                <li><strong>Directorio de Trabajo:</strong> {summary['system_info']['working_directory']}</li>
                                <li><strong>Versión de Python:</strong> {summary['system_info']['python_version']}</li>
                                <li><strong>Timestamp:</strong> {summary['timestamp']}</li>
                            </ul>
                        </div>
                    </div>
                    
                    {"<div class='alert alert-danger mt-4'><h5>⚠️ Errores Encontrados:</h5><ul>" + "".join([f"<li>{error}</li>" for error in summary['error_messages']]) + "</ul></div>" if summary['error_messages'] else ""}
                    
                    {"<div class='alert alert-warning mt-4'><h5>⚠️ Advertencias:</h5><ul>" + "".join([f"<li>{warning}</li>" for warning in summary['warning_messages']]) + "</ul></div>" if summary['warning_messages'] else ""}
                    
                </div>
            </div>
        </div>
        
        <button class="btn btn-primary refresh-btn" onclick="window.location.reload()">
            🔄 Actualizar Diagnóstico
        </button>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Auto-refresh cada 30 segundos si hay errores
            {"setTimeout(() => window.location.reload(), 30000);" if summary['overall_status'] == 'ERROR' else ""}
        </script>
    </body>
    </html>
    """
    
    return html_template

async def health_check_endpoint():
    """Endpoint para el diagnóstico de salud del sistema"""
    try:
        checker = HealthChecker()
        diagnosis = checker.run_full_diagnosis()
        html_response = get_health_check_html(diagnosis)
        return HTMLResponse(content=html_response)
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error en Diagnóstico</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h2>❌ Error en el Diagnóstico</h2>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <p><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
                    <button class="btn btn-primary" onclick="window.location.reload()">🔄 Reintentar</button>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

async def health_check_json():
    """Endpoint para obtener diagnóstico en formato JSON"""
    try:
        checker = HealthChecker()
        diagnosis = checker.run_full_diagnosis()
        return diagnosis
    except Exception as e:
        logger.error(f"Error en health check JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en diagnóstico: {str(e)}") 