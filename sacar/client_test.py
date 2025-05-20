# client_test.py - Cliente para probar el endpoint process_question
import requests
import json

# URL del endpoint FastAPI (corregido para usar process_question)
url = "http://localhost:8000/api/process_question"

# Datos de prueba
payload = {
    "question_input": "¿como es la afiliacion de la esposa de un afiliado ?",
    "fecha_desde": "2024-01-01",
    "fecha_hasta": "2024-12-31",
    "k": 4
}

print(f"[DEBUG] Enviando solicitud a: {url}")
print(f"[DEBUG] Payload: {json.dumps(payload, indent=2)}")

# Hacer la solicitud POST
response = requests.post(url, json=payload)

print(f"[DEBUG] Código de estado: {response.status_code}")
print(f"[DEBUG] Headers de respuesta: {dict(response.headers)}")

# Mostrar el resultado
if response.status_code == 200:
    print("[DEBUG] Respuesta completa:", json.dumps(response.json(), indent=2))
    print("Respuesta del asistente:\n")
    print(response.json()["answer"])
    # Si hay metadata, mostrarla también
    if "metadata" in response.json():
        print("\nMetadata:")
        print(f"Modelo: {response.json()['metadata'].get('model', 'No disponible')}")
        print(f"Documentos recuperados: {response.json()['metadata'].get('document_count', 0)}")
else:
    print(f"Error en la solicitud: {response.status_code}")
    print(response.text)
