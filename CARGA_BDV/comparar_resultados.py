#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para comparar los resultados de las consultas vectoriales entre Qdrant y Chroma.
"""

import os
import re
import sys
import argparse
from datetime import datetime

def extraer_consultas(contenido):
    """Extrae las consultas y sus resultados de un archivo de salida."""
    consultas = []
    
    # Patrón para encontrar bloques de consulta
    patron_consulta = r"={50}\nCONSULTA (QDRANT|CHROMA) - (.*?)\nPregunta: (.*?)\nResultados encontrados: (\d+)\n={50}(.*?)(?=\n={50}|\Z)"
    
    # Buscar todas las ocurrencias
    coincidencias = re.findall(patron_consulta, contenido, re.DOTALL)
    
    for tipo, fecha, pregunta, num_resultados, contenido_resultados in coincidencias:
        # Extraer fragmentos individuales
        fragmentos = []
        patron_fragmento = r"----- Fragmento #(\d+) \(Score: ([\d.]+)\) -----\nContenido:\n(.*?)(?=\nMetadatos:|\n-{70})"
        
        coincidencias_fragmentos = re.findall(patron_fragmento, contenido_resultados, re.DOTALL)
        
        for num, score, contenido_fragmento in coincidencias_fragmentos:
            # Extraer metadatos si existen
            metadatos = {}
            patron_metadatos = r"Metadatos:\n(.*?)(?=\n-{70})"
            coincidencias_metadatos = re.search(patron_metadatos, contenido_resultados[contenido_resultados.find(contenido_fragmento):], re.DOTALL)
            
            if coincidencias_metadatos:
                lineas_metadatos = coincidencias_metadatos.group(1).strip().split('\n')
                for linea in lineas_metadatos:
                    if " - " in linea:
                        clave, valor = linea.split(" - ", 1)
                        metadatos[clave.strip()] = valor.strip()
            
            fragmentos.append({
                'numero': int(num),
                'score': float(score),
                'contenido': contenido_fragmento.strip(),
                'metadatos': metadatos
            })
        
        consultas.append({
            'tipo': tipo,
            'fecha': fecha.strip(),
            'pregunta': pregunta.strip(),
            'num_resultados': int(num_resultados),
            'fragmentos': fragmentos
        })
    
    return consultas

def comparar_resultados(archivo_qdrant, archivo_chroma):
    """Compara los resultados entre Qdrant y Chroma."""
    try:
        # Leer archivos
        with open(archivo_qdrant, 'r', encoding='utf-8') as f:
            contenido_qdrant = f.read()
        
        with open(archivo_chroma, 'r', encoding='utf-8') as f:
            contenido_chroma = f.read()
        
        # Extraer consultas
        consultas_qdrant = extraer_consultas(contenido_qdrant)
        consultas_chroma = extraer_consultas(contenido_chroma)
        
        print(f"\n===== COMPARACIÓN DE RESULTADOS =====")
        print(f"Archivo Qdrant: {archivo_qdrant} ({len(consultas_qdrant)} consultas)")
        print(f"Archivo Chroma: {archivo_chroma} ({len(consultas_chroma)} consultas)")
        
        # Agrupar por preguntas
        preguntas_qdrant = {c['pregunta']: c for c in consultas_qdrant}
        preguntas_chroma = {c['pregunta']: c for c in consultas_chroma}
        
        # Encontrar preguntas comunes
        preguntas_comunes = set(preguntas_qdrant.keys()) & set(preguntas_chroma.keys())
        
        if not preguntas_comunes:
            print("\nNo se encontraron consultas comunes para comparar.")
            return
        
        print(f"\nSe encontraron {len(preguntas_comunes)} consultas comunes para comparar.\n")
        
        # Comparar resultados para cada pregunta común
        for i, pregunta in enumerate(sorted(preguntas_comunes), 1):
            print(f"\n{i}. CONSULTA: {pregunta}")
            
            # Obtener resultados para esta pregunta
            res_qdrant = preguntas_qdrant[pregunta]
            res_chroma = preguntas_chroma[pregunta]
            
            print(f"   Qdrant: {res_qdrant['num_resultados']} resultados")
            print(f"   Chroma: {res_chroma['num_resultados']} resultados")
            
            # Comparar contenido de resultados
            fragmentos_qdrant = set(f['contenido'] for f in res_qdrant['fragmentos'])
            fragmentos_chroma = set(f['contenido'] for f in res_chroma['fragmentos'])
            
            fragmentos_comunes = fragmentos_qdrant & fragmentos_chroma
            solo_qdrant = fragmentos_qdrant - fragmentos_chroma
            solo_chroma = fragmentos_chroma - fragmentos_qdrant
            
            print(f"   Fragmentos comunes: {len(fragmentos_comunes)}")
            print(f"   Fragmentos solo en Qdrant: {len(solo_qdrant)}")
            print(f"   Fragmentos solo en Chroma: {len(solo_chroma)}")
            
            # Comparar scores para fragmentos comunes
            if fragmentos_comunes:
                print("\n   Comparación de scores para fragmentos comunes:")
                
                for contenido in fragmentos_comunes:
                    # Buscar el fragmento en ambos resultados
                    frag_qdrant = next((f for f in res_qdrant['fragmentos'] if f['contenido'] == contenido), None)
                    frag_chroma = next((f for f in res_chroma['fragmentos'] if f['contenido'] == contenido), None)
                    
                    if frag_qdrant and frag_chroma:
                        dif_score = frag_qdrant['score'] - frag_chroma['score']
                        print(f"   - Fragmento {frag_qdrant['numero']} (Qdrant) / {frag_chroma['numero']} (Chroma)")
                        print(f"     Score Qdrant: {frag_qdrant['score']:.4f}")
                        print(f"     Score Chroma: {frag_chroma['score']:.4f}")
                        print(f"     Diferencia: {dif_score:.4f}")
            
            print("-" * 70)
            
        # Estadísticas generales
        total_fragmentos_comunes = 0
        total_solo_qdrant = 0
        total_solo_chroma = 0
        
        for pregunta in preguntas_comunes:
            fragmentos_qdrant = set(f['contenido'] for f in preguntas_qdrant[pregunta]['fragmentos'])
            fragmentos_chroma = set(f['contenido'] for f in preguntas_chroma[pregunta]['fragmentos'])
            
            fragmentos_comunes = fragmentos_qdrant & fragmentos_chroma
            solo_qdrant = fragmentos_qdrant - fragmentos_chroma
            solo_chroma = fragmentos_chroma - fragmentos_qdrant
            
            total_fragmentos_comunes += len(fragmentos_comunes)
            total_solo_qdrant += len(solo_qdrant)
            total_solo_chroma += len(solo_chroma)
        
        print("\n===== ESTADÍSTICAS GENERALES =====")
        print(f"Total de fragmentos comunes: {total_fragmentos_comunes}")
        print(f"Total de fragmentos solo en Qdrant: {total_solo_qdrant}")
        print(f"Total de fragmentos solo en Chroma: {total_solo_chroma}")
        
        # Calcular porcentaje de coincidencia
        total_fragmentos = total_fragmentos_comunes + total_solo_qdrant + total_solo_chroma
        if total_fragmentos > 0:
            porcentaje_coincidencia = (total_fragmentos_comunes / total_fragmentos) * 100
            print(f"Porcentaje de coincidencia: {porcentaje_coincidencia:.2f}%")
        
    except Exception as e:
        print(f"Error al comparar resultados: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description='Comparar resultados de consultas vectoriales entre Qdrant y Chroma.')
    parser.add_argument('--qdrant', default='resultados_qdrant.txt', help='Archivo con los resultados de Qdrant')
    parser.add_argument('--chroma', default='resultados_chroma.txt', help='Archivo con los resultados de Chroma')
    args = parser.parse_args()
    
    if not os.path.exists(args.qdrant):
        print(f"Error: El archivo {args.qdrant} no existe.")
        return 1
    
    if not os.path.exists(args.chroma):
        print(f"Error: El archivo {args.chroma} no existe.")
        return 1
    
    comparar_resultados(args.qdrant, args.chroma)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 