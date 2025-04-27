# complete_client_test.py
import requests
import json
from datetime import datetime
import sys

def print_separator(character='=', length=80):
    print(character * length)

def query_complete_analysis(question, fecha_desde=None, fecha_hasta=None, k=None):
    """
    Consulta el endpoint de análisis completo con los parámetros especificados
    
    Args:
        question (str): Pregunta a procesar
        fecha_desde (str): Fecha de inicio en formato YYYY-MM-DD
        fecha_hasta (str): Fecha de fin en formato YYYY-MM-DD
        k (int): Número de documentos a recuperar
        
    Returns:
        dict: Respuesta del servidor
    """
    # Configurar valores por defecto
    if not fecha_desde:
        fecha_desde = "2024-01-01"
    if not fecha_hasta:
        fecha_hasta = "2024-12-31"
    if not k:
        k = 4
        
    # URL del endpoint FastAPI
    url = "http://localhost:8000/complete_analysis"
    
    # Datos de la solicitud
    payload = {
        "question_input": question,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "k": k
    }
    
    print_separator()
    print(f"ENVIANDO CONSULTA AL ASISTENTE SIMAP")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    print(f"Pregunta: {question}")
    print(f"Periodo: {fecha_desde} a {fecha_hasta}")
    print(f"Documentos a recuperar (k): {k}")
    print_separator()
    
    try:
        # Hacer la solicitud POST
        print("Enviando solicitud...")
        response = requests.post(url, json=payload, timeout=60)
        
        # Verificar la respuesta
        if response.status_code == 200:
            data = response.json()
            print_separator()
            print("RESPUESTA RECIBIDA")
            print_separator()
            
            # Mostrar metadata
            metadata = data.get('metadata', {})
            print(f"Modelo utilizado: {metadata.get('model', 'No disponible')}")
            print(f"Documentos recuperados: {metadata.get('document_count', 0)}")
            print_separator()
            
            # Mostrar respuesta
            print("RESPUESTA DEL ASISTENTE:")
            print_separator()
            print(data['answer'])
            print_separator()
            
            return data
        else:
            print(f"Error en la solicitud: {response.status_code}")
            print(response.text)
            return None
    
    except Exception as e:
        print(f"Error al realizar la solicitud: {str(e)}")
        return None

def main():
    # Comprobar argumentos de línea de comandos
    if len(sys.argv) < 2:
        print("Uso: python complete_client_test.py \"¿Tu pregunta aquí?\" [fecha_desde] [fecha_hasta] [k]")
        print("Ejemplo: python complete_client_test.py \"¿Cómo tramitar la insulina tipo glargina?\" 2024-01-01 2024-12-31 4")
        return
    
    # Obtener la pregunta de los argumentos
    question = sys.argv[1]
    
    # Obtener parámetros opcionales
    fecha_desde = sys.argv[2] if len(sys.argv) > 2 else None
    fecha_hasta = sys.argv[3] if len(sys.argv) > 3 else None
    k = int(sys.argv[4]) if len(sys.argv) > 4 else None
    
    # Realizar la consulta
    query_complete_analysis(question, fecha_desde, fecha_hasta, k)

if __name__ == "__main__":
    main() 