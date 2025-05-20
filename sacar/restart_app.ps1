# Script para reiniciar la aplicación y asegurar que se usen las variables correctas
Write-Host "Deteniendo cualquier instancia previa de uvicorn..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -eq "uvicorn" -or $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Limpiando variables de entorno antiguas..." -ForegroundColor Yellow
# En caso de que haya variables de entorno que estén interfiriendo
if (Test-Path env:OPENAI_API_KEY) {
    Remove-Item env:OPENAI_API_KEY
}

Write-Host "Validando la API key de OpenAI..." -ForegroundColor Green
python validar_openai_key.py

Write-Host "Iniciando la aplicación con las variables actualizadas..." -ForegroundColor Green
uvicorn app.main:app --reload 