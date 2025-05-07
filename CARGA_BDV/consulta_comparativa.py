#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para ejecutar consultas en Qdrant y Chroma simultáneamente y comparar resultados.
"""

import os
import sys
import configparser
import argparse
from datetime import datetime
import subprocess
import tempfile
from comparar_resultados import comparar_resultados

def buscar_config_ini():
    """Busca el archivo config.ini en diferentes ubicaciones."""
    # Lista de posibles ubicaciones del archivo config.ini
    posibles_rutas = [
        'config.ini',                           # En el directorio actual
        '../config.ini',                        # En el directorio padre
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),  # En la carpeta del script
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')  # En la carpeta padre del script
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            print(f"Archivo config.ini encontrado en: {ruta}")
            return ruta
    
    print("ADVERTENCIA: No se encontró el archivo config.ini")
    return None

def main():
    # Configuración de argumentos
    parser = argparse.ArgumentParser(description='Ejecutar consultas en Qdrant y Chroma y comparar resultados.')
    parser.add_argument('--pregunta', '-p', type=str, help='Pregunta a consultar')
    parser.add_argument('--num', '-n', type=int, default=5, help='Número de resultados a recuperar')
    parser.add_argument('--salida', '-s', type=str, default='resultados_comparativa.txt', help='Archivo para guardar la comparación')
    args = parser.parse_args()
    
    print("\n===== CONSULTA COMPARATIVA QDRANT VS CHROMA =====\n")
    
    # Verificar si existe el archivo config.ini
    ruta_config = buscar_config_ini()
    if not ruta_config:
        print("Error: No se pudo encontrar el archivo config.ini")
        return 1
    
    # Crear archivos temporales para guardar los resultados
    archivo_qdrant = tempfile.NamedTemporaryFile(delete=False, suffix='_qdrant.txt', mode='w', encoding='utf-8')
    archivo_chroma = tempfile.NamedTemporaryFile(delete=False, suffix='_chroma.txt', mode='w', encoding='utf-8')
    
    # Determinar la ruta raíz del proyecto
    # Asumimos que consulta_comparativa.py está en CARGA_BDV, y la raíz es un nivel arriba de CARGA_BDV
    project_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root_path = project_root_path.replace('\\', '/') # Asegurar barras inclinadas hacia adelante para compatibilidad

    try:
        # Cerrar los archivos temporales para que puedan ser utilizados por otros procesos
        archivo_qdrant.close()
        archivo_chroma.close()
        
        # Convertir rutas a formato seguro con barras normales
        ruta_qdrant = archivo_qdrant.name.replace('\\', '/')
        ruta_chroma = archivo_chroma.name.replace('\\', '/')
        
        # Información sobre archivos temporales
        print(f"Archivo temporal para Qdrant: {ruta_qdrant}")
        print(f"Archivo temporal para Chroma: {ruta_chroma}")
        print(f"Ruta raíz del proyecto detectada: {project_root_path}")
        
        # Preparar la consulta
        if not args.pregunta:
            args.pregunta = input("\nIngrese la pregunta a consultar: ")
            if not args.pregunta.strip():
                print("Error: La pregunta no puede estar vacía.")
                return 1
        
        print(f"\nPregunta a consultar: {args.pregunta}")
        print(f"Número de resultados: {args.num}")
        
        # Script para automatizar la consulta en Qdrant
        script_qdrant = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
# Añadir la ruta raíz del proyecto al sys.path
sys.path.append(r'{project_root_path}')
from CARGA_BDV.consulta_qdrant import main as qdrant_main
from unittest.mock import patch
import builtins

# Simular la entrada del usuario para automatizar la consulta
original_input = builtins.input
inputs = iter([
    's',  # Sí a guardar en archivo
    r'{ruta_qdrant}',  # Ruta del archivo
    '{args.pregunta}',  # Pregunta
    '{args.num}',  # Número de resultados
    'salir'  # Salir del programa
])

def mock_input(prompt):
    print(prompt, end='')
    val = next(inputs)
    print(val)
    return val

# Parchar la función input
with patch('builtins.input', mock_input):
    qdrant_main()
"""
        
        # Script para automatizar la consulta en Chroma
        script_chroma = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
# Añadir la ruta raíz del proyecto al sys.path
sys.path.append(r'{project_root_path}')
from CARGA_BDV.consulta_chroma import main as chroma_main
from unittest.mock import patch
import builtins

# Simular la entrada del usuario para automatizar la consulta
original_input = builtins.input
inputs = iter([
    's',  # Sí a guardar en archivo
    r'{ruta_chroma}',  # Ruta del archivo
    '{args.pregunta}',  # Pregunta
    '{args.num}',  # Número de resultados
    'salir'  # Salir del programa
])

def mock_input(prompt):
    print(prompt, end='')
    val = next(inputs)
    print(val)
    return val

# Parchar la función input
with patch('builtins.input', mock_input):
    chroma_main()
"""
        
        # Crear archivos temporales con los scripts y especificar codificación UTF-8
        with tempfile.NamedTemporaryFile(delete=False, suffix='_script_qdrant.py', mode='w', encoding='utf-8') as script_file_qdrant:
            script_file_qdrant.write(script_qdrant)
            script_qdrant_path = script_file_qdrant.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='_script_chroma.py', mode='w', encoding='utf-8') as script_file_chroma:
            script_file_chroma.write(script_chroma)
            script_chroma_path = script_file_chroma.name
        
        # Ejecutar consulta en Qdrant
        print("\n" + "="*50)
        print("EJECUTANDO CONSULTA EN QDRANT...")
        print("="*50)
        
        subprocess.run([sys.executable, script_qdrant_path], check=True)
        
        # Ejecutar consulta en Chroma
        print("\n" + "="*50)
        print("EJECUTANDO CONSULTA EN CHROMA...")
        print("="*50)
        
        subprocess.run([sys.executable, script_chroma_path], check=True)
        
        # Comparar resultados
        print("\n" + "="*50)
        print("COMPARANDO RESULTADOS...")
        print("="*50)
        
        comparar_resultados(archivo_qdrant.name, archivo_chroma.name)
        
        # Guardar la comparación en un archivo si se especificó
        if args.salida:
            print(f"\nGuardando comparación en {args.salida}...")
            
            # Redireccionar la salida a un archivo
            with open(args.salida, 'w', encoding='utf-8') as f:
                # Escribir encabezado
                f.write(f"===== COMPARACIÓN DE RESULTADOS =====\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Pregunta: {args.pregunta}\n")
                f.write(f"Número de resultados: {args.num}\n\n")
                
                # Copiar contenido de los archivos de resultados
                f.write("===== RESULTADOS DE QDRANT =====\n")
                with open(archivo_qdrant.name, 'r', encoding='utf-8') as f_qdrant:
                    f.write(f_qdrant.read())
                
                f.write("\n\n===== RESULTADOS DE CHROMA =====\n")
                with open(archivo_chroma.name, 'r', encoding='utf-8') as f_chroma:
                    f.write(f_chroma.read())
                
                # Ejecutar comparación y capturar la salida
                import io
                from contextlib import redirect_stdout
                
                with io.StringIO() as buf, redirect_stdout(buf):
                    comparar_resultados(archivo_qdrant.name, archivo_chroma.name)
                    comparacion = buf.getvalue()
                
                f.write("\n\n===== ANÁLISIS COMPARATIVO =====\n")
                f.write(comparacion)
            
            print(f"Comparación guardada en {args.salida}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Eliminar archivos temporales
        try:
            for archivo in [archivo_qdrant.name, archivo_chroma.name, script_qdrant_path, script_chroma_path]:
                if os.path.exists(archivo):
                    os.unlink(archivo)
        except Exception as e:
            print(f"Error al eliminar archivos temporales: {str(e)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 