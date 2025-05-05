@echo off
REM Script para configurar y ejecutar Qdrant en Windows
TITLE Configuración de Qdrant para PAMI

echo =============================================
echo  Configuración de Qdrant para PAMI
echo =============================================
echo.

REM Verificar si Python está instalado
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no está instalado o no está en el PATH.
    echo Por favor, instala Python 3.8 o superior desde https://www.python.org/downloads/
    echo y asegúrate de marcar la opción "Add Python to PATH" durante la instalación.
    pause
    exit /b 1
)

REM Verificar si Docker está instalado
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ADVERTENCIA: Docker no está instalado o no está en el PATH.
    echo Para usar Qdrant necesitarás Docker. 
    echo Puedes descargarlo desde https://www.docker.com/products/docker-desktop
    echo.
    echo Presiona cualquier tecla para continuar de todos modos...
    pause > nul
)

echo.
echo 1. Instalando dependencias necesarias...
echo.
python instalar_dependencias_qdrant.py
if %errorlevel% neq 0 (
    echo.
    echo Hubo un problema durante la instalación de dependencias.
    echo Por favor, revisa los mensajes de error anteriores.
    pause
    exit /b 1
)

echo.
echo 2. Iniciando servidor Qdrant con Docker...
echo.

REM Verificar si el contenedor ya está en ejecución
docker ps | find "qdrant" > nul 2>&1
if %errorlevel% equ 0 (
    echo El servidor Qdrant ya está en ejecución.
) else (
    REM Intentar iniciar con docker-compose
    docker-compose -f docker-compose-qdrant.yml up -d
    if %errorlevel% neq 0 (
        echo ADVERTENCIA: No se pudo iniciar con docker-compose, intentando con comando docker run...
        docker run -d -p 6333:6333 -p 6334:6334 --name qdrant_server qdrant/qdrant
        if %errorlevel% neq 0 (
            echo ERROR: No se pudo iniciar el servidor Qdrant.
            echo Asegúrate de que Docker esté en ejecución.
            pause
            exit /b 1
        )
    )
    echo Servidor Qdrant iniciado correctamente.
)

echo.
echo =============================================
echo  ¡Configuración completada!
echo =============================================
echo.
echo Ahora puedes:
echo.
echo 1. Cargar datos en Qdrant (todos los registros)
echo    python carga_bdv_q1.py
echo.
echo 2. Cargar datos en Qdrant (modo prueba - 10 registros)
echo    python carga_bdv_q1.py --modo-prueba
echo.
echo 3. Probar la búsqueda en Qdrant
echo    python test_qdrant.py
echo.
echo 4. Acceder al panel de administración de Qdrant
echo    http://localhost:6333/dashboard
echo.

echo ¿Qué deseas hacer?
echo.
echo [1] - Cargar datos en Qdrant (todos los registros)
echo [2] - Cargar datos en Qdrant (modo prueba - 10 registros)
echo [3] - Probar búsqueda en Qdrant
echo [4] - Salir
echo.

set /p opcion="Selecciona una opción (1-4): "

if "%opcion%"=="1" (
    echo.
    echo Ejecutando carga de datos (todos los registros)...
    python carga_bdv_q1.py
    pause
) else if "%opcion%"=="2" (
    echo.
    echo Ejecutando carga de datos en modo prueba (10 registros)...
    python carga_bdv_q1.py --modo-prueba
    pause
) else if "%opcion%"=="3" (
    echo.
    echo Ejecutando prueba de búsqueda...
    python test_qdrant.py
    pause
) else (
    echo.
    echo Programa finalizado.
    echo Para detener el servidor Qdrant, ejecuta: docker-compose -f docker-compose-qdrant.yml down
    echo.
    pause
)

exit /b 0 