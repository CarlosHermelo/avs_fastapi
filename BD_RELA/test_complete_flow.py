#!/usr/bin/env python
# BD_RELA/test_complete_flow.py
import requests
import json
import time

def test_complete_analysis():
    """Probar el endpoint de análisis completo"""
    print("=== PROBANDO ENDPOINT /api/complete_analysis ===")
    
    url = "http://localhost:8000/api/complete_analysis"
    
    test_data = {
        "question_input": "¿Cómo puedo obtener información sobre mis beneficios en PAMI?",
        "id_usuario": 321,
        "ugel_origen": "Formosa"
    }
    
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print("-" * 60)
    
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
            print(f"Respuesta: {response_data['answer'][:100]}...")
            
            metadata = response_data.get('metadata', {})
            id_consulta = metadata.get('id_consulta')
            
            print(f"\n📊 Metadatos:")
            print(f"  ID Consulta: {id_consulta}")
            print(f"  Modelo: {metadata.get('model', 'N/A')}")
            print(f"  Documentos recuperados: {metadata.get('document_count', 'N/A')}")
            print(f"  Tokens entrada: {metadata.get('input_tokens', 'N/A')}")
            print(f"  Tokens salida: {metadata.get('output_tokens', 'N/A')}")
            print(f"  Tiempo respuesta: {metadata.get('processing_time_ms', 'N/A')} ms")
            print(f"  Tipo BD: {metadata.get('db_type', 'N/A')}")
            
            if id_consulta:
                print(f"\n🎯 ID de consulta obtenido: {id_consulta}")
                print("Ahora probando el feedback...")
                return test_feedback(id_consulta)
            else:
                print("❌ No se obtuvo ID de consulta")
                return False
                
        else:
            print("❌ Error en la respuesta:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Texto de respuesta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: No se pudo conectar al servidor.")
        print("Asegúrate de que el servidor FastAPI esté ejecutándose en http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Error de timeout: La petición tardó demasiado.")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_feedback(id_consulta):
    """Probar el endpoint de feedback"""
    print(f"\n=== PROBANDO ENDPOINT /api/feedback (ID: {id_consulta}) ===")
    
    url = "http://localhost:8000/api/feedback"
    
    # Probar feedback positivo
    test_data_si = {
        "id_consulta": id_consulta,
        "feedback_value": "me_gusta"
    }
    
    print(f"URL: {url}")
    print(f"Datos (me_gusta): {json.dumps(test_data_si, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(
            url,
            json=test_data_si,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Feedback 'me_gusta' exitoso:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # Esperar un poco y probar feedback negativo
            time.sleep(1)
            
            test_data_no = {
                "id_consulta": id_consulta,
                "feedback_value": "no_me_gusta"
            }
            
            print(f"\nProbando feedback 'no_me_gusta'...")
            response2 = requests.post(
                url,
                json=test_data_no,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"Status Code: {response2.status_code}")
            
            if response2.status_code == 200:
                response2_data = response2.json()
                print("✅ Feedback 'no_me_gusta' exitoso:")
                print(json.dumps(response2_data, indent=2, ensure_ascii=False))
                return True
            else:
                print("❌ Error en feedback 'no_me_gusta':")
                try:
                    error_data = response2.json()
                    print(json.dumps(error_data, indent=2, ensure_ascii=False))
                except:
                    print(f"Texto de respuesta: {response2.text}")
                return False
                
        else:
            print("❌ Error en feedback 'me_gusta':")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Texto de respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en feedback: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando prueba del flujo completo...")
    print("Asegúrate de que:")
    print("1. El servidor FastAPI esté ejecutándose")
    print("2. DB_TYPE=mysql en el archivo .env")
    print("3. MySQL esté accesible")
    print("\nPresiona Enter para continuar...")
    input()
    
    success = test_complete_analysis()
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 ¡PRUEBA COMPLETA EXITOSA!")
        print("✅ El flujo completo funciona correctamente con MySQL")
        print("✅ Los radio buttons deberían funcionar en el frontend")
    else:
        print("❌ PRUEBA FALLIDA")
        print("Revisa los logs del servidor FastAPI para más detalles")
    print("="*60) 