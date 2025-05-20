import os
import openai
from dotenv import load_dotenv

def check_openai_api_key(api_key, key_name):
    """
    Valida una clave API de OpenAI intentando listar los modelos.
    """
    if not api_key:
        print(f"La clave '{key_name}' no está definida o no se pudo cargar.")
        return False

    # Imprimir una porción de la clave para depuración
    # (ej. primeros 5 y últimos 4 caracteres)
    obscured_key = ""
    if len(api_key) > 9:
        obscured_key = f"{api_key[:5]}...{api_key[-4:]}"
    elif api_key: # Si la clave es corta pero existe
        obscured_key = f"{api_key[:1]}...{api_key[-1:]}" if len(api_key) > 2 else f"{api_key[:1]}..."

    print(f"Intentando validar '{key_name}' con valor (parcial): '{obscured_key}'")

    try:
        # Es importante crear una instancia de OpenAI client para cada intento
        # por si una clave anterior deja el estado global en una condición inválida.
        client = openai.OpenAI(api_key=api_key)
        client.models.list() # Intento de llamada a la API
        print(f"La clave API de OpenAI '{key_name}' ES VÁLIDA.")
        return True
    except openai.AuthenticationError:
        print(f"La clave API de OpenAI '{key_name}' NO ES VÁLIDA (Error de autenticación).")
        return False
    except openai.APIConnectionError:
        print(f"La clave API de OpenAI '{key_name}' NO ES VÁLIDA (Error de conexión con la API). Verifica tu conexión a internet.")
        return False
    except Exception as e:
        print(f"Error inesperado al validar la clave '{key_name}': {e}")
        return False

if __name__ == "__main__":
    env_file_name = ".env"
    # Construye la ruta al archivo .env en la raíz del proyecto (un nivel arriba de CARGA_BDV)
    env_file_path = os.path.join(os.path.dirname(__file__), "..", env_file_name)
    env_file_path = os.path.abspath(env_file_path)

    print(f"Intentando cargar el archivo de entorno desde: {env_file_path}")

    if os.path.exists(env_file_path):
        # Cargar el archivo .env, sobrescribiendo variables de entorno existentes
        loaded = load_dotenv(dotenv_path=env_file_path, override=True)
        if loaded:
            print(f"Archivo de entorno '{env_file_path}' cargado exitosamente (con override=True).")
        else:
            print(f"ADVERTENCIA: No se pudo cargar el archivo de entorno '{env_file_path}' usando dotenv.")
    else:
        print(f"ADVERTENCIA: No se encontró el archivo de entorno en '{env_file_path}'.")

    print("\n--- Valores de las claves leídos del entorno DESPUÉS de intentar cargar .env ---")
    keys_to_check_values = {}
    for key_name in ["openai_api_key", "api_key", "OPENAI_API_KEY"]:
        key_value = os.getenv(key_name)
        keys_to_check_values[key_name] = key_value
        obscured_val = "No definida"
        if key_value:
            if len(key_value) > 9:
                obscured_val = f"{key_value[:5]}...{key_value[-4:]}"
            elif key_value: 
                obscured_val = f"{key_value[:1]}...{key_value[-1:]}" if len(key_value) > 2 else f"{key_value[:1]}..."
        print(f"Valor para '{key_name}' (os.getenv): {obscured_val}")
    print("--------------------------------------------------------------------------\n")

    valid_keys_found = []
    invalid_keys = []

    print("Validando claves API de OpenAI...\n")
    # Usar los valores que acabamos de imprimir para la validación
    for key_name, key_value in keys_to_check_values.items(): 
        print(f"--- Validando '{key_name}' ---")
        if key_value is None:
            # Este caso ya fue cubierto por la impresión anterior, pero se mantiene la lógica
            print(f"La variable de entorno '{key_name}' no está definida.")
            invalid_keys.append(key_name)
            continue
        
        is_valid = check_openai_api_key(key_value, key_name)
        if is_valid:
            valid_keys_found.append(key_name)
        else:
            invalid_keys.append(key_name)
        print("---------------------------\n")

    if valid_keys_found:
        print(f"Resumen: Claves VÁLIDAS encontradas: {', '.join(valid_keys_found)}")
    else:
        print("Resumen: No se encontró NINGUNA clave de OpenAI válida.")

    if invalid_keys:
        actual_invalid_keys = [key for key in invalid_keys if keys_to_check_values.get(key) is not None]
        if actual_invalid_keys:
            print(f"Resumen: Claves NO VÁLIDAS o con problemas: {', '.join(actual_invalid_keys)}")
        
        not_defined_keys = [key for key in invalid_keys if keys_to_check_values.get(key) is None]
        if not_defined_keys:
            print(f"Resumen: Claves NO DEFINIDAS en el entorno: {', '.join(not_defined_keys)}")

    print("\nInstrucciones para ejecutar este script:")
    print("1. Asegúrate de que el archivo '.env' exista en la raíz de tu proyecto (un nivel arriba de la carpeta CARGA_BDV).")
    print("   El archivo '.env' debe contener las claves, por ejemplo:")
    print("   openai_api_key=sk-xxxxxxxxxxxxxxxxxxxx")
    print("   api_key=sk-yyyyyyyyyyyyyyyyyyyy")
    print("   OPENAI_API_KEY=sk-zzzzzzzzzzzzzzzzzzzz")
    print("2. Asegúrate de tener las librerías necesarias instaladas (python-dotenv, openai).")
    print(f"3. Navega a la carpeta CARGA_BDV en tu terminal: cd CARGA_BDV")
    print(f"4. Ejecuta el script: python validar_claves_openai.py") 