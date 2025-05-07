@echo off
REM Script para verificar y liberar espacio en el sistema
TITLE Liberación de espacio para Qdrant

echo =============================================
echo  Verificación de espacio en disco
echo =============================================
echo.

REM Verificar espacio disponible en unidades
echo Espacio disponible en unidades:
echo.
wmic logicaldisk get deviceid, freespace, size

echo.
echo =============================================
echo  Opciones para liberar espacio
echo =============================================

echo.
echo 1. Limpieza de archivos temporales...
echo.
echo Presiona cualquier tecla para eliminar archivos temporales...
pause > nul

REM Eliminar archivos temporales del sistema
del /q /f /s %TEMP%\*.*
del /q /f /s C:\Windows\Temp\*.*

echo.
echo 2. Verificando la ubicación de Qdrant...
echo.

REM Buscar ubicación de la base de datos de Qdrant
set "QDRANT_PATH="
for %%d in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%d:\qdrant" (
        set "QDRANT_PATH=%%d:\qdrant"
    )
    if exist "%%d:\Qdrant" (
        set "QDRANT_PATH=%%d:\Qdrant"
    )
)

if not "%QDRANT_PATH%"=="" (
    echo Se encontró Qdrant en: %QDRANT_PATH%
) else (
    echo No se encontró la instalación de Qdrant.
)

echo.
echo 3. Sugerencias para liberar espacio:
echo.
echo a) Desinstalar aplicaciones no utilizadas
echo    Ejecuta: control appwiz.cpl
echo.
echo b) Usar Limpieza de disco
echo    Ejecuta: cleanmgr
echo.
echo c) Cambiar la ubicación de almacenamiento de Qdrant en config.ini
echo    Modifica: qdrant_url, apuntando a una unidad con más espacio
echo.

echo =============================================
echo  Verificando config.ini
echo =============================================
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
    echo.
    echo Contenido de la sección SERVICIOS_SIMAP_Q:
    findstr /C:"[SERVICIOS_SIMAP_Q]" /C:"qdrant_url" %CONFIG_PATH%
    echo.
    echo Para cambiar la ubicación de Qdrant, modifica el parámetro "qdrant_url"
    echo en el archivo config.ini para apuntar a una unidad con más espacio.
) else (
    echo No se encontró el archivo config.ini.
)

echo.
echo =============================================
echo  Recomendaciones finales
echo =============================================
echo.
echo 1. Libera más espacio en la unidad principal
echo 2. Cambia la ubicación de Qdrant a una unidad con más espacio
echo 3. Reduce el tamaño del conjunto de datos o usa el modo prueba
echo.
echo Para ejecutar en modo prueba con solo 10 registros:
echo   python carga_bdv_q1.py --modo-prueba
echo.

pause 