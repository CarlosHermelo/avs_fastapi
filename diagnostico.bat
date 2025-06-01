@echo off
rem ========================================
rem Script de Diagnostico - Asistente SIMAP
rem ========================================

setlocal enabledelayedexpansion

echo.
echo =====================================================
echo           DIAGNOSTICO DEL SISTEMA SIMAP
echo =====================================================
echo.

rem Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH
    echo.
    echo Soluciones:
    echo 1. Instalar Python desde https://python.org
    echo 2. Agregar Python al PATH del sistema
    echo.
    pause
    exit /b 1
)

echo [OK] Python disponible

rem Verificar que el script de diagnóstico existe
if not exist "diagnostico_sistema.py" (
    echo [ERROR] No se encuentra el archivo diagnostico_sistema.py
    echo Asegúrate de ejecutar este script desde el directorio del proyecto
    echo.
    pause
    exit /b 1
)

echo [OK] Script de diagnóstico encontrado

rem Verificar entorno virtual (solo información, no bloquea)
python -c "import sys; print('venv activo:', hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))" 2>nul
python -c "import sys, os; print('Entorno:', os.path.basename(sys.prefix) if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix else 'Sistema')" 2>nul
echo.

rem Menú de opciones
:menu
echo Selecciona una opcion:
echo.
echo 1. Diagnostico basico
echo 2. Diagnostico detallado (verbose)
echo 3. Generar reporte JSON
echo 4. Diagnostico web (abrir navegador)
echo 5. Verificar entorno de ejecucion
echo 6. Verificar base de datos (MySQL/SQLite)
echo 7. Verificar antes de iniciar aplicacion
echo 8. Ayuda
echo 9. Salir
echo.
set /p opcion="Ingresa tu opcion (1-9): "

if "%opcion%"=="1" goto diagnostico_basico
if "%opcion%"=="2" goto diagnostico_detallado
if "%opcion%"=="3" goto generar_json
if "%opcion%"=="4" goto diagnostico_web
if "%opcion%"=="5" goto verificar_entorno
if "%opcion%"=="6" goto verificar_base_datos
if "%opcion%"=="7" goto verificar_inicio
if "%opcion%"=="8" goto mostrar_ayuda
if "%opcion%"=="9" goto salir

echo [ERROR] Opcion invalida. Intenta de nuevo.
echo.
goto menu

:diagnostico_basico
echo.
echo [INFO] Ejecutando diagnostico basico...
echo =====================================
python diagnostico_sistema.py
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:diagnostico_detallado
echo.
echo [INFO] Ejecutando diagnostico detallado...
echo =====================================
python diagnostico_sistema.py --verbose
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:generar_json
echo.
set "timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "timestamp=!timestamp: =0!"
set "archivo=diagnostico_!timestamp!.json"

echo [INFO] Generando reporte JSON: !archivo!
echo =====================================
python diagnostico_sistema.py --json --output "!archivo!"

if errorlevel 1 (
    echo [ERROR] Error al generar el reporte
) else (
    echo [OK] Reporte generado exitosamente: !archivo!
    echo.
    set /p abrir="Deseas abrir el archivo? (s/n): "
    if /i "!abrir!"=="s" (
        start notepad "!archivo!"
    )
)
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:diagnostico_web
echo.
echo [INFO] Verificando si la aplicacion web esta ejecutandose...
echo ======================================================

rem Verificar si el puerto 8000 está en uso
netstat -an | findstr ":8000" >nul
if errorlevel 1 (
    echo [ERROR] La aplicacion web no esta ejecutandose en el puerto 8000
    echo.
    echo Para usar el diagnostico web:
    echo 1. Inicia la aplicacion: python app/main.py
    echo 2. Espera a que este completamente cargada
    echo 3. Vuelve a intentar esta opcion
    echo.
    set /p iniciar="Deseas intentar iniciar la aplicacion ahora? (s/n): "
    if /i "!iniciar!"=="s" (
        echo Iniciando aplicacion...
        start "Asistente SIMAP" python app/main.py
        echo.
        echo Esperando 10 segundos para que la aplicacion inicie...
        timeout /t 10 >nul
        echo.
        echo Abriendo navegador...
        start http://localhost:8000/api/health
    )
) else (
    echo [OK] Aplicacion detectada en puerto 8000
    echo [INFO] Abriendo diagnostico web en el navegador...
    start http://localhost:8000/api/health
)
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:verificar_entorno
echo.
echo [INFO] Verificando entorno de ejecucion...
echo =====================================
echo.

rem Verificar si estamos en Windows
python -c "import platform; print('Sistema operativo:', platform.system())" 2>nul

rem Verificar entorno virtual
python -c "import sys, os; venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix); print('Entorno virtual activo:', 'Si' if venv_active else 'No'); print('Nombre del entorno:', os.path.basename(sys.prefix) if venv_active else 'Sistema global')" 2>nul

rem Verificar si es tot17
python -c "import sys, os; venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix); venv_name = os.path.basename(sys.prefix) if venv_active else ''; print('Es tot17?:', 'Si [OK]' if venv_name.lower() == 'tot17' else 'No [WARNING]')" 2>nul

rem Verificar si está en Docker
python -c "import os; print('En Docker?:', 'Si' if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') == 'true' else 'No')" 2>nul

echo.
echo Ejecutando verificacion completa del entorno...
python diagnostico_sistema.py --verbose | findstr /C:"Entorno de Ejecucion" /C:"WARNING" /C:"OK" /C:"ERROR"

echo.
echo [INFO] Recomendaciones:
echo - En Windows: Usar entorno virtual 'tot17' (.\tot17\Scripts\activate)
echo - En Docker: Configuracion optima para produccion
echo - En Linux: Verificar dependencias del sistema
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:verificar_base_datos
echo.
echo [INFO] Verificando sistema de base de datos dual...
echo ===============================================
echo.

rem Crear archivo temporal para capturar resultado JSON
python diagnostico_sistema.py --json > temp_db_check.json 2>nul

rem Extraer información de base de datos del JSON
findstr /C:"database_dual_connection" temp_db_check.json >nul
if not errorlevel 1 (
    echo [INFO] Estado de la conexion dual MySQL/SQLite:
    echo.
    
    rem Buscar el estado activo
    findstr /C:"active_connection" temp_db_check.json > temp_active.txt 2>nul
    if exist temp_active.txt (
        for /f "tokens=2 delims=:" %%a in (temp_active.txt) do (
            set "active_db=%%a"
            set "active_db=!active_db: =!"
            set "active_db=!active_db:"=!"
            set "active_db=!active_db:,=!"
        )
        
        if "!active_db!"=="MySQL" (
            echo [OK] Base de datos activa: MySQL (Configuracion optima^)
            echo    - Ideal para produccion
            echo    - Rendimiento superior
            echo    - Transacciones robustas
        ) else if "!active_db!"=="SQLite" (
            echo [WARNING] Base de datos activa: SQLite (Fallback automatico^)
            echo    - MySQL no esta disponible
            echo    - Funcionando con SQLite como respaldo
            echo    - Recomendacion: Verificar configuracion MySQL
        ) else (
            echo [ERROR] No hay conexion activa a ninguna base de datos
            echo    - Verificar configuracion
            echo    - Revisar archivos de BD
        )
        
        del temp_active.txt 2>nul
    )
    
    echo.
    echo [INFO] Configuracion actual:
    echo    - DB_TYPE en config: %DB_TYPE%
    findstr /C:"mysql_status" temp_db_check.json >nul
    if not errorlevel 1 (
        echo    - Estado MySQL: Verificado
    ) else (
        echo    - Estado MySQL: No verificado
    )
    
    findstr /C:"sqlite_status" temp_db_check.json >nul
    if not errorlevel 1 (
        echo    - Estado SQLite: Verificado
    ) else (
        echo    - Estado SQLite: No verificado
    )
)

del temp_db_check.json 2>nul

echo.
echo [INFO] Informacion sobre base de datos dual:
echo    - La aplicacion intenta MySQL primero
echo    - Si MySQL falla, usa SQLite automaticamente
echo    - SQLite es funcional pero MySQL es recomendado para produccion
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:verificar_inicio
echo.
echo [INFO] Verificando sistema antes del inicio...
echo =========================================
python diagnostico_sistema.py --verbose

if errorlevel 2 (
    echo.
    echo [ERROR] SISTEMA CON ERRORES CRITICOS
    echo No se recomienda iniciar la aplicacion.
    echo Revisa los errores mostrados arriba.
    echo.
) else if errorlevel 1 (
    echo.
    echo [WARNING] SISTEMA CON ADVERTENCIAS
    echo La aplicacion puede funcionar, pero hay problemas menores.
    echo.
    echo Posibles causas de advertencias:
    echo - Entorno virtual no es 'tot17'
    echo - MySQL no disponible (usando SQLite)
    echo - Configuraciones menores
    echo.
    set /p continuar="Deseas iniciar la aplicacion de todas formas? (s/n): "
    if /i "!continuar!"=="s" goto iniciar_aplicacion
) else (
    echo.
    echo [OK] SISTEMA OK - LISTO PARA INICIAR
    echo.
    set /p iniciar="Deseas iniciar la aplicacion ahora? (s/n): "
    if /i "!iniciar!"=="s" goto iniciar_aplicacion
)
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:iniciar_aplicacion
echo.
echo [INFO] Iniciando Asistente SIMAP...
echo Esto abrira una nueva ventana con la aplicacion.
echo.
start "Asistente SIMAP" python app/main.py
echo [OK] Aplicacion iniciada en nueva ventana
echo.
echo Puedes:
echo - Esperar unos segundos y usar la opcion 4 para diagnostico web
echo - Ir a http://localhost:8000/api/health en tu navegador
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:mostrar_ayuda
echo.
echo [HELP] Sistema de Diagnostico
echo ==================================
echo.
echo Este sistema verifica el estado de todos los componentes:
echo.
echo [OK] Componentes verificados:
echo   - Entorno de ejecucion (Windows/Docker/Linux)
echo   - Entorno virtual en Windows (recomendado: tot17)
echo   - Uvicorn (servidor web)
echo   - Qdrant (base de datos vectorial)
echo   - Base de datos dual (MySQL principal, SQLite fallback)
echo   - OpenAI (API y embeddings)
echo   - Archivos criticos del sistema
echo   - Variables de entorno
echo.
echo [INFO] Interpretacion de resultados:
echo   [OK]      = Funcionando correctamente
echo   [WARNING] = Funcional con advertencias
echo   [ERROR]   = Problemas criticos
echo.
echo [INFO] Entornos de ejecucion:
echo   - Windows + tot17    = [OK] (Recomendado desarrollo)
echo   - Windows + otro venv = [WARNING]
echo   - Windows sin venv   = [WARNING]
echo   - Docker Container   = [OK] (Recomendado produccion)
echo   - Linux             = [OK]
echo.
echo [INFO] Base de datos dual:
echo   - MySQL activo      = [OK] (Optimo)
echo   - SQLite activo     = [WARNING] (Fallback)
echo   - Ninguna activa    = [ERROR]
echo.
echo [INFO] Uso manual desde CMD:
echo   python diagnostico_sistema.py              # Basico
echo   python diagnostico_sistema.py --verbose    # Detallado
echo   python diagnostico_sistema.py --json       # JSON
echo   python diagnostico_sistema.py --help       # Ayuda completa
echo.
echo [INFO] Endpoints web (cuando la aplicacion este activa):
echo   http://localhost:8000/api/health           # Diagnostico HTML
echo   http://localhost:8000/api/health/json      # Diagnostico JSON
echo   http://localhost:8000/api/status           # Estado basico
echo.
echo [INFO] Solucion de problemas comunes:
echo   - Entorno virtual: .\tot17\Scripts\activate
echo   - MySQL no disponible: Verificar XAMPP/WAMP o Docker
echo   - Qdrant no conecta: docker run -p 6333:6333 qdrant/qdrant
echo.
echo Para mas informacion, consulta README_DIAGNOSTICO.md
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto menu

:salir
echo.
echo Hasta luego!
echo.
exit /b 0

endlocal 