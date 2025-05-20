import os
import sys
import openai
import configparser
from dotenv import load_dotenv, find_dotenv

def validar_openai_key(api_key):
    """Valida una clave API de OpenAI."""
    try:
        # Configurar el cliente de OpenAI
        client = openai.OpenAI(api_key=api_key)
        
        # Realizar una solicitud simple para verificar la API key
        response = client.models.list()
        
        # Si llegamos aquí, la API key es válida
        print(f"\n✅ La API key de OpenAI es válida")
        print(f"Modelos disponibles: {len(response.data)}")
        
        # Imprimir algunos modelos disponibles
        print("\nAlgunos modelos disponibles:")
        for i, model in enumerate(response.data[:5]):
            print(f"  - {model.id}")
            if i >= 4:
                break
                
        return True
    
    except Exception as e:
        print(f"\n❌ Error al validar la API key de OpenAI: {str(e)}")
        return False

def actualizar_config_ini(api_key_env):
    """Actualiza el archivo config.ini con la API key de OpenAI válida."""
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Actualizar la API key en la sección DEFAULT
        if 'DEFAULT' in config:
            # Conservar el valor comentado como referencia
            api_key_actual = config['DEFAULT'].get('openai_api_key', '')
            if api_key_actual == 'sk-tu-clave-de-openai-aqui' or not api_key_actual.startswith('sk-'):
                # Actualizar la API key
                config['DEFAULT']['openai_api_key'] = api_key_env
                
                # Guardar los cambios en config.ini
                with open('config.ini', 'w') as f:
                    config.write(f)
                
                print(f"\n✅ API key de OpenAI actualizada en config.ini")
                return True
            else:
                print("\n⚠️ No se actualizó config.ini porque ya tiene una API key configurada")
        else:
            print("\n❌ No se pudo actualizar config.ini porque falta la sección DEFAULT")
        
        return False
    
    except Exception as e:
        print(f"\n❌ Error al actualizar config.ini: {str(e)}")
        return False

def actualizar_env_file(api_key_config):
    """Actualiza el archivo .env con la API key de OpenAI válida desde config.ini."""
    try:
        # Encontrar la ruta del archivo .env
        dotenv_path = find_dotenv()
        
        if not dotenv_path:
            # Si no existe, crear en el directorio actual
            dotenv_path = os.path.join(os.getcwd(), '.env')
            print(f"Creando nuevo archivo .env en: {dotenv_path}")
        else:
            print(f"Actualizando archivo .env existente en: {dotenv_path}")
        
        # Leer el contenido actual si el archivo existe
        env_content = ""
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r') as f:
                env_content = f.read()
        
        # Crear un nuevo contenido con la API key actualizada
        lines = env_content.split('\n') if env_content else []
        new_lines = []
        openai_key_found = False
        
        for line in lines:
            if line.startswith('OPENAI_API_KEY='):
                new_lines.append(f'OPENAI_API_KEY={api_key_config}')
                openai_key_found = True
            else:
                new_lines.append(line)
        
        # Si no se encontró la clave, agregarla al final
        if not openai_key_found:
            new_lines.append(f'OPENAI_API_KEY={api_key_config}')
        
        # Eliminar líneas vacías al final
        while new_lines and new_lines[-1] == '':
            new_lines.pop()
        
        # Asegurarse de que termine con una nueva línea
        if new_lines:
            new_lines.append('')
        
        # Escribir el contenido actualizado
        with open(dotenv_path, 'w') as f:
            f.write('\n'.join(new_lines))
        
        # Verificar que la escritura fue exitosa
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r') as f:
                contenido = f.read()
                if f'OPENAI_API_KEY={api_key_config}' in contenido:
                    print(f"\n✅ API key de OpenAI actualizada correctamente en el archivo .env")
                    return True
                else:
                    print(f"\n⚠️ No se pudo verificar la actualización del archivo .env")
        
        return False
    
    except Exception as e:
        print(f"\n❌ Error al actualizar el archivo .env: {str(e)}")
        return False

def validar_config():
    """Valida la configuración de las API keys."""
    resultado_final = False
    print("== Iniciando validación de API keys de OpenAI ==")
    
    # 1. Validar API key en .env
    print("\n== Validando API key en .env ==")
    dotenv_path = find_dotenv()
    if dotenv_path:
        print(f"Archivo .env encontrado en: {dotenv_path}")
    else:
        print("No se encontró un archivo .env")
    
    # Cargar variables de entorno
    load_dotenv(override=True)
    api_key_env = os.getenv("OPENAI_API_KEY")
    
    if not api_key_env:
        print("⚠️ No se encontró la variable OPENAI_API_KEY en el archivo .env")
        resultado_env = False
    else:
        print(f"API key encontrada en .env: {api_key_env[:5]}...{api_key_env[-4:]}")
        resultado_env = validar_openai_key(api_key_env)
    
    # 2. Validar config.ini
    print("\n== Validando API key en config.ini ==")
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Verificar si existe la sección DEFAULT
        if 'DEFAULT' not in config:
            print("❌ La sección DEFAULT no existe en config.ini")
            resultado_config = False
            api_key_config = None
        else:
            # Verificar API key de OpenAI en config.ini
            api_key_config = config['DEFAULT'].get('openai_api_key', '')
            if not api_key_config or api_key_config == 'sk-tu-clave-de-openai-aqui':
                print("⚠️ La clave API de OpenAI no está configurada correctamente en config.ini")
                resultado_config = False
                
                # Preguntar si quiere actualizar config.ini con la API key de .env
                if resultado_env and api_key_env:
                    print("\n¿Desea actualizar config.ini con la API key válida de .env? (s/n)")
                    respuesta = input().lower().strip()
                    if respuesta == 's' or respuesta == 'si' or respuesta == 'y' or respuesta == 'yes':
                        actualizar_config_ini(api_key_env)
                        # Volver a validar
                        config.read('config.ini')
                        api_key_config = config['DEFAULT'].get('openai_api_key', '')
                        resultado_config = validar_openai_key(api_key_config)
            else:
                print(f"API key encontrada en config.ini: {api_key_config[:5]}...{api_key_config[-4:]}")
                resultado_config = validar_openai_key(api_key_config)
            
            # Si la clave en config.ini es válida pero la de .env no, ofrecer actualizar .env
            if resultado_config and not resultado_env:
                print("\n¿Desea actualizar el archivo .env con la API key válida de config.ini? (s/n)")
                respuesta = input().lower().strip()
                if respuesta == 's' or respuesta == 'si' or respuesta == 'y' or respuesta == 'yes':
                    if actualizar_env_file(api_key_config):
                        # Volver a cargar las variables de entorno
                        load_dotenv(override=True)
                        api_key_env = os.getenv("OPENAI_API_KEY")
                        if api_key_env:
                            print(f"Nueva API key en .env: {api_key_env[:5]}...{api_key_env[-4:]}")
                            # Verificar que la nueva clave sea válida
                            resultado_env = validar_openai_key(api_key_env)
            
    except Exception as e:
        print(f"❌ Error al leer config.ini: {str(e)}")
        resultado_config = False
        api_key_config = None
    
    # Resultado final - Si al menos una API key es válida
    resultado_final = resultado_env or resultado_config
    
    print("\n== Resumen de validación ==")
    print(f"API key en .env: {'✅ Válida' if resultado_env else '❌ Inválida o no encontrada'}")
    print(f"API key en config.ini: {'✅ Válida' if resultado_config else '❌ Inválida o no encontrada'}")
    
    # Sugerencias finales
    if not resultado_final:
        print("\n⚠️ No se encontró ninguna API key válida de OpenAI. Por favor:")
        print("- Obtenga una API key válida de OpenAI en https://platform.openai.com/api-keys")
        print("- Configúrela en .env o en config.ini")
    else:
        print("\n✅ Al menos una configuración tiene una API key válida")
    
    return resultado_final

if __name__ == "__main__":
    print("Validando API keys de OpenAI...")
    resultado = validar_config()
    sys.exit(0 if resultado else 1) 