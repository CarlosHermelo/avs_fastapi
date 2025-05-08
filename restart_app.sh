#!/bin/bash

# Script para reiniciar la aplicación y asegurar que se usen las variables correctas
echo "Deteniendo cualquier instancia previa de uvicorn..."
pkill -f "uvicorn app.main:app"

echo "Limpiando variables de entorno antiguas..."
# En caso de que haya variables de entorno del sistema que estén interfiriendo
unset OPENAI_API_KEY

echo "Validando la API key de OpenAI..."
python validar_openai_key.py

echo "Iniciando la aplicación con las variables actualizadas..."
uvicorn app.main:app --reload 