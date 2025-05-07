@echo off
REM Script para limpiar espacio en disco usado por Docker
TITLE Limpieza de Docker para PAMI

echo =============================================
echo  Limpieza de espacio en disco para Docker
echo =============================================
echo.

REM Verificar si Docker está instalado
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker no está instalado o no está en el PATH.
    echo Este script requiere Docker para funcionar.
    pause
    exit /b 1
)

echo Deteniendo contenedores de Qdrant...
docker-compose -f docker-compose-qdrant.yml down
docker stop qdrant_server > nul 2>&1

echo.
echo 1. Eliminando contenedores detenidos...
docker container prune -f

echo.
echo 2. Eliminando imágenes no utilizadas...
docker image prune -f

echo. 
echo 3. Eliminando volúmenes no utilizados...
docker volume prune -f

echo.
echo 4. Eliminando redes no utilizadas...
docker network prune -f

echo.
echo 5. Limpieza completa del sistema Docker...
docker system prune -f

echo.
echo =============================================
echo  Limpieza completada
echo =============================================
echo.

echo Creando directorio para datos de Qdrant...
if not exist "qdrant_data" mkdir qdrant_data

echo.
echo Reiniciando servicio Qdrant con el nuevo volumen...
docker-compose -f docker-compose-qdrant.yml up -d

echo.
echo Espacio en disco liberado. Ahora puedes intentar ejecutar nuevamente:
echo   python carga_bdv_q1.py --modo-prueba
echo.

pause 