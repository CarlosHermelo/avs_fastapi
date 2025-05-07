@echo off
REM Script para instalar y configurar Qdrant localmente sin Docker
TITLE Instalación local de Qdrant para PAMI

echo =============================================
echo  Instalación local de Qdrant (sin Docker)
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

REM Verificar si pip está instalado
pip --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip no está instalado o no está en el PATH.
    echo Este script requiere pip para funcionar.
    pause
    exit /b 1
)

echo.
echo 1. Seleccione la unidad donde desea instalar Qdrant
echo.
echo Unidades disponibles:
echo.

REM Listar unidades disponibles
for %%d in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%d:\" (
        for /f "tokens=3" %%s in ('dir /-c %%d:\ ^| findstr /c:"bytes free"') do (
            echo %%d: - %%s bytes libres
        )
    )
)

echo.
set /p unidad="Seleccione una unidad (C, D, etc.): "

if not exist "%unidad%:\" (
    echo.
    echo ERROR: La unidad %unidad%: no existe o no está accesible.
    pause
    exit /b 1
)

echo.
echo Instalando Qdrant en la unidad %unidad%:
echo.

REM Crear directorio para Qdrant
if not exist "%unidad%:\qdrant_data" (
    mkdir "%unidad%:\qdrant_data"
)

echo.
echo 2. Instalando el cliente de Qdrant y todas las dependencias...
echo.

pip install qdrant-client langchain-qdrant langchain-openai langchain

echo.
echo 3. Instalando el servidor Qdrant localmente...
echo.

pip install qdrant-server

echo.
echo 4. Creando archivo de configuración para Qdrant...
echo.

set QDRANT_CONFIG_FILE=%unidad%:\qdrant_data\config.yaml
echo # Configuración para Qdrant > %QDRANT_CONFIG_FILE%
echo storage: >> %QDRANT_CONFIG_FILE%
echo   storage_path: %unidad%:/qdrant_data/storage >> %QDRANT_CONFIG_FILE%
echo service: >> %QDRANT_CONFIG_FILE%
echo   host: 127.0.0.1 >> %QDRANT_CONFIG_FILE%
echo   http_port: 6333 >> %QDRANT_CONFIG_FILE%
echo   enable_cors: true >> %QDRANT_CONFIG_FILE%

echo.
echo 5. Creando archivo batch para iniciar Qdrant...
echo.

set QDRANT_START_FILE=%unidad%:\qdrant_data\iniciar_qdrant.bat
echo @echo off > %QDRANT_START_FILE%
echo REM Script para iniciar el servidor Qdrant >> %QDRANT_START_FILE%
echo TITLE Servidor Qdrant >> %QDRANT_START_FILE%
echo echo Iniciando servidor Qdrant... >> %QDRANT_START_FILE%
echo echo. >> %QDRANT_START_FILE%
echo echo Para detener el servidor, presiona Ctrl+C y confirma con S >> %QDRANT_START_FILE%
echo echo. >> %QDRANT_START_FILE%
echo cd %unidad%:\qdrant_data >> %QDRANT_START_FILE%
echo qdrant --config-path config.yaml >> %QDRANT_START_FILE%

echo.
echo 6. Actualizando config.ini para usar el nuevo servidor Qdrant...
echo.

REM Buscar config.ini
set "CONFIG_FOUND=0"
set "CONFIG_PATH="
for %%p in ("config.ini" "..\config.ini") do (
    if exist "%%~p" (
        set "CONFIG_FOUND=1"
        set "CONFIG_PATH=%%~p"
    )
)

if "%CONFIG_FOUND%"=="1" (
    echo Archivo config.ini encontrado en: %CONFIG_PATH%
    
    REM Verificar si existe la sección SERVICIOS_SIMAP_Q
    findstr /C:"[SERVICIOS_SIMAP_Q]" %CONFIG_PATH% > nul
    if %errorlevel% equ 0 (
        echo Sección SERVICIOS_SIMAP_Q encontrada
        
        REM Actualizar qdrant_url con la nueva ruta
        echo Asegúrate de actualizar manualmente el parámetro qdrant_url en %CONFIG_PATH%:
        echo qdrant_url = http://localhost:6333?path=%unidad%:/qdrant_data/storage
    ) else (
        echo No se encontró la sección SERVICIOS_SIMAP_Q en config.ini
        echo Deberás añadirla manualmente.
    )
) else (
    echo No se encontró el archivo config.ini.
    echo Deberás configurar manualmente la ruta de Qdrant.
)

echo.
echo =============================================
echo  Instalación completada
echo =============================================
echo.
echo Para usar Qdrant:
echo.
echo 1. Inicia el servidor Qdrant ejecutando:
echo    %unidad%:\qdrant_data\iniciar_qdrant.bat
echo.
echo 2. Actualiza el parámetro 'qdrant_url' en config.ini:
echo    qdrant_url = http://localhost:6333?path=%unidad%:/qdrant_data/storage
echo.
echo 3. Ejecuta la carga con:
echo    python carga_bdv_q1.py --modo-prueba --comprobar-espacio
echo.
echo 4. O especifica directamente la ruta:
echo    python carga_bdv_q1.py --modo-prueba --qdrant-path=%unidad%:/qdrant_data/storage
echo.

pause 