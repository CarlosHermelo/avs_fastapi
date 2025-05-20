#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente de prueba para el endpoint de análisis con Qdrant
"""

import requests
import json
import argparse
import os
import datetime
import sys

def test_complete_analysis(base_url, question, fecha_desde=None, fecha_hasta=None, k=None):
    """
    Realizar una consulta al endpoint /api/complete_analysis
    
    Args:
        base_url (str): URL base del servidor
        question (str): La pregunta a procesar
        fecha_desde (str, optional): Fecha de inicio para filtrado
        fecha_hasta (str, optional): Fecha de fin para filtrado
        k (int, optional): Número de documentos a recuperar
        
    Returns:
        dict: La respuesta del servidor
    """
    # Endpoint para el análisis completo
    url = f"{base_url}/api/complete_analysis"
    
    # Preparar la solicitud
    payload = {
        "question_input": question,
        "fecha_desde": fecha_desde or "2023-01-01",
        "fecha_hasta": fecha_hasta or "2024-12-31",
        "k": k or 5
    }
    
    # Realizar la solicitud POST
    try:
        print(f"Enviando solicitud a {url}")
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Lanzar una excepción si hay un error HTTP
        
        # Devolver los datos de la respuesta
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al comunicarse con el servidor: {str(e)}")
        return None

def test_simple_question(base_url, question):
    """
    Realizar una consulta al endpoint /api/process_question
    
    Args:
        base_url (str): URL base del servidor
        question (str): La pregunta a procesar
        
    Returns:
        dict: La respuesta del servidor
    """
    # Endpoint para procesar pregunta simple
    url = f"{base_url}/api/process_question"
    
    # Preparar la solicitud
    payload = {
        "question_input": question,
        "fecha_desde": "2023-01-01",
        "fecha_hasta": "2024-12-31",
        "k": 5
    }
    
    # Realizar la solicitud POST
    try:
        print(f"Enviando solicitud a {url}")
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Lanzar una excepción si hay un error HTTP
        
        # Devolver los datos de la respuesta
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al comunicarse con el servidor: {str(e)}")
        return None

def main():
    """Función principal del cliente de prueba"""
    parser = argparse.ArgumentParser(description="Cliente de prueba para el API de PAMI con Qdrant")
    parser.add_argument("--url", type=str, default="http://localhost:8000",
                        help="URL base del servidor (default: http://localhost:8000)")
    parser.add_argument("--endpoint", type=str, choices=["simple", "complete"], default="complete",
                        help="Tipo de endpoint a utilizar (simple o complete)")
    parser.add_argument("--question", type=str, 
                        default="¿Cómo es la afiliación de la esposa de un afiliado?",
                        help="Pregunta a realizar")
    parser.add_argument("--k", type=int, default=5,
                        help="Número de documentos a recuperar")
    parser.add_argument("--fecha-desde", type=str, default="2023-01-01",
                        help="Fecha desde la cual filtrar resultados (YYYY-MM-DD)")
    parser.add_argument("--fecha-hasta", type=str, default="2024-12-31",
                        help="Fecha hasta la cual filtrar resultados (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default=None,
                        help="Archivo para guardar la respuesta")
    
    args = parser.parse_args()
    
    print(f"Cliente de prueba para API PAMI con Qdrant")
    print(f"URL base: {args.url}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Pregunta: {args.question}")
    
    # Realizar la consulta según el endpoint seleccionado
    start_time = datetime.datetime.now()
    
    if args.endpoint == "simple":
        response = test_simple_question(args.url, args.question)
    else:  # complete
        response = test_complete_analysis(
            args.url,
            args.question,
            fecha_desde=args.fecha_desde,
            fecha_hasta=args.fecha_hasta,
            k=args.k
        )
    
    end_time = datetime.datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    # Mostrar la respuesta
    if response:
        print("\n=== RESPUESTA ===")
        if "answer" in response:
            print(response["answer"])
        
        print(f"\nTiempo de respuesta: {processing_time:.2f} segundos")
        
        # Mostrar metadatos si están disponibles
        if "metadata" in response and response["metadata"]:
            print("\n=== METADATOS ===")
            for key, value in response["metadata"].items():
                print(f"{key}: {value}")
        
        # Guardar la respuesta si se especificó un archivo de salida
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump({
                    "question": args.question,
                    "response": response,
                    "processing_time": processing_time,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "endpoint": args.endpoint
                }, f, ensure_ascii=False, indent=2)
            print(f"\nRespuesta guardada en {args.output}")
    else:
        print("No se recibió respuesta del servidor.")
        sys.exit(1)

if __name__ == "__main__":
    main() 