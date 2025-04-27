#!/bin/bash

# Inicializar el repositorio Git
git init

# Agregar archivos al primer commit
git add .gitignore
git add README.md
git add DOCKER.md
git add Dockerfile
git add docker-compose.yml
git add requirements.txt
git add app/
git add .dockerignore
git add config.ini

# No agregar los directorios data/ y tot17/
echo "Directorios data/ y tot17/ excluidos del repositorio"

# Crear el primer commit
git commit -m "Inicialización del proyecto Asistente PAMI"

# Instrucciones para conectar con GitHub
echo "
----------------------------------------------
Repositorio Git inicializado correctamente.
----------------------------------------------

Para conectarlo con GitHub:

1. Crea un nuevo repositorio en GitHub (sin README, .gitignore, o LICENSE)

2. Conecta tu repositorio local con GitHub:
   git remote add origin https://github.com/tu-usuario/pami-assistant.git

3. Sube tu código a GitHub:
   git push -u origin master

----------------------------------------------
"

# Dar permisos de ejecución al script
chmod +x init_repo.sh 