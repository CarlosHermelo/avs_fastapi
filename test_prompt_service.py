#!/usr/bin/env python
# test_prompt_service.py
"""
Script de prueba para verificar el funcionamiento del servicio de prompt
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.prompt_service import get_system_prompt

def test_prompt_service():
    """
    Prueba el servicio de prompt y muestra de dónde se obtuvo el prompt
    """
    print("="*80)
    print("PRUEBA DEL SERVICIO DE PROMPT")
    print("="*80)
    
    try:
        prompt_content, source = get_system_prompt()
        
        print(f"Fuente del prompt: {source}")
        print(f"Longitud del prompt: {len(prompt_content)} caracteres")
        print(f"Primeros 200 caracteres del prompt:")
        print("-" * 40)
        print(prompt_content[:200] + "..." if len(prompt_content) > 200 else prompt_content)
        print("-" * 40)
        
        # Mostrar información sobre las fuentes disponibles
        print("\nInformación de fuentes:")
        
        # Verificar base de datos
        from app.services.prompt_service import get_active_prompt_from_db
        db_prompt = get_active_prompt_from_db()
        print(f"✓ Base de datos: {'Disponible' if db_prompt else 'No disponible'}")
        
        # Verificar archivo
        from app.services.prompt_service import get_prompt_from_file
        file_prompt = get_prompt_from_file()
        print(f"✓ Archivo prompt_fallback.txt: {'Disponible' if file_prompt else 'No disponible'}")
        
        # Verificar archivo prompt_fallback.txt existe
        prompt_file_path = Path("prompt_fallback.txt")
        print(f"✓ Archivo prompt_fallback.txt existe: {'Sí' if prompt_file_path.exists() else 'No'}")
        
        print("\n" + "="*80)
        print("PRUEBA COMPLETADA EXITOSAMENTE")
        print("="*80)
        
    except Exception as e:
        print(f"Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prompt_service() 