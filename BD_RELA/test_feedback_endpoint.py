#!/usr/bin/env python
# BD_RELA/test_feedback_endpoint.py
import requests
import json

def test_feedback_endpoint():
    """Probar el endpoint de feedback directamente"""
    
    # URL del endpoint
    url = "http://localhost:8000/api/feedback"
    
    # Datos de prueba - usar ID 41 que sabemos que existe
    test_data = {
        "id_consulta": 41,
        "feedback_value": "me_gusta"
    }
    
    print(f"Probando endpoint: {url}")
    print(f"Datos de prueba: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        # Realizar la petición POST
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Respuesta exitosa:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
        else:
            print("❌ Error en la respuesta:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Texto de respuesta: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: No se pudo conectar al servidor.")
        print("Asegúrate de que el servidor FastAPI esté ejecutándose en http://localhost:8000")
    except requests.exceptions.Timeout:
        print("❌ Error de timeout: La petición tardó demasiado.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_feedback_endpoint() 