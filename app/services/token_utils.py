# app/services/token_utils.py
import tiktoken
from app.core.logging_config import log_message

def contar_tokens(texto, modelo="gpt-3.5-turbo"):
    """
    Cuenta la cantidad de tokens en un texto para un modelo específico
    
    Args:
        texto (str): El texto para el cual contar tokens
        modelo (str): El modelo de OpenAI para el cual contar tokens
        
    Returns:
        int: La cantidad de tokens
    """
    try:
        if modelo.startswith("gpt-4"):
            codificador = tiktoken.encoding_for_model("gpt-4")
        elif modelo.startswith("gpt-3.5"):
            codificador = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            codificador = tiktoken.get_encoding("cl100k_base")
        
        tokens = len(codificador.encode(texto))
        return tokens
    except Exception as e:
        log_message(f"Error al contar tokens: {str(e)}", level='ERROR')
        return 0

def count_words(text):
    """
    Cuenta la cantidad de palabras en un texto
    
    Args:
        text (str): El texto para contar palabras
        
    Returns:
        int: La cantidad de palabras
    """
    return len(text.split())

def validar_palabras(prompt, max_palabras=10000):
    """
    Valida si un texto supera el límite de palabras
    
    Args:
        prompt (str): El texto a validar
        max_palabras (int): El límite máximo de palabras
        
    Returns:
        tuple: (es_valido, num_palabras)
    """
    num_palabras = count_words(prompt)
    if num_palabras > max_palabras:
        log_message(f"\nEl contenido supera el límite de {max_palabras} palabras ({num_palabras} palabras utilizadas).")
        return False, num_palabras
    return True, num_palabras

def reducir_contenido_por_palabras(text, max_palabras=10000):
    """
    Reduce un texto a un máximo de palabras
    
    Args:
        text (str): El texto a reducir
        max_palabras (int): El límite máximo de palabras
        
    Returns:
        str: El texto reducido
    """
    palabras = text.split()
    if len(palabras) > max_palabras:
        log_message("El contenido es demasiado largo, truncando...")
        return " ".join(palabras[:max_palabras]) + "\n\n[Contenido truncado...]"
    return text
