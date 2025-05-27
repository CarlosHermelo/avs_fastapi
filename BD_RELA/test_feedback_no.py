#!/usr/bin/env python
import requests
import json

def test_feedback_no():
    """Probar el endpoint de feedback con 'no_me_gusta'"""
    
    url = "http://localhost:8000/api/feedback"
    
    # Usar ID 40 para probar "no_me_gusta"
    test_data = {
        "id_consulta": 40,
        "feedback_value": "no_me_gusta"
    }
    
    print(f"Probando endpoint: {url}")
    print(f"Datos de prueba: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
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
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_feedback_no() 