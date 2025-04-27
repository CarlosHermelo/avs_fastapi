# client_test.py
import requests
import json

# URL del endpoint FastAPI
url = "http://localhost:8000/process_question"

# Datos de prueba
payload = {
    "question_input": "¿como afilio  a mi pareja ?",
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
else:
    print(f"Error en la solicitud: {response.status_code}")
    print(response.text)
