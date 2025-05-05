#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para instalar y verificar las dependencias necesarias para trabajar con Qdrant
"""

import subprocess
import sys
import importlib.util
import os

def check_package(package_name):
    """Verifica si un paquete está instalado"""
    return importlib.util.find_spec(package_name) is not None

def install_package(package):
    """Instala un paquete usando pip"""
    print(f"Instalando {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print(f"{package} instalado correctamente.")

def main():
    # Lista de paquetes necesarios
    packages = [
        "qdrant-client",
        "langchain-qdrant",
        "langchain-openai",
        "langchain"
    ]
    
    print("=== Verificando dependencias para Qdrant ===")
    
    # Verificar cada paquete
    missing_packages = []
    for package in packages:
        pkg_name = package.split("==")[0].replace("-", "_")
        if not check_package(pkg_name):
            missing_packages.append(package)
    
    # Instalar paquetes faltantes
    if missing_packages:
        print(f"Se necesitan instalar {len(missing_packages)} paquetes:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        
        consent = input("\n¿Desea instalar los paquetes faltantes? (s/n): ")
        if consent.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            for pkg in missing_packages:
                install_package(pkg)
            print("\nTodas las dependencias han sido instaladas correctamente.")
        else:
            print("\nOperación cancelada. Las dependencias no fueron instaladas.")
            return 1
    else:
        print("Todas las dependencias necesarias ya están instaladas.")
    
    # Verificar si Qdrant está en ejecución
    print("\n=== Verificando conexión con Qdrant ===")
    
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://localhost:6333")
        client.get_collections()
        print("Conexión exitosa con Qdrant en http://localhost:6333")
    except Exception as e:
        print(f"Error al conectar con Qdrant: {str(e)}")
        print("\nAsegúrate de que el servidor Qdrant esté en ejecución. Puedes iniciarlo con Docker usando:")
        print("\ndocker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return 1
    
    print("\n=== Resumen ===")
    print("✓ Todas las dependencias están instaladas")
    print("✓ Conexión con Qdrant establecida")
    print("\nAhora puedes ejecutar:")
    print("  python carga_bdv_q1.py  # Para cargar datos en Qdrant")
    print("  python test_qdrant.py   # Para probar la búsqueda en Qdrant")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 