# app/services/token_utils.py
import tiktoken
from app.core.logging_config import log_message
from functools import lru_cache
import hashlib

try:
    # Intentar importar las bibliotecas opcionales para diferentes proveedores
    import tiktoken  # OpenAI
    
    try:
        from anthropic import Anthropic  # Anthropic
    except ImportError:
        Anthropic = None
    
    try:
        from transformers import AutoTokenizer  # Hugging Face
    except ImportError:
        AutoTokenizer = None
    
    try:
        import google.generativeai as genai  # Google
    except ImportError:
        genai = None
except ImportError as e:
    log_message(f"Advertencia: Algunas librerías de tokenización no están disponibles: {str(e)}", level='WARNING')

@lru_cache(maxsize=10)
def get_tokenizer(model_name: str):
    """
    Obtiene el tokenizador adecuado para el modelo con cache
    
    Args:
        model_name (str): Nombre del modelo de lenguaje
        
    Returns:
        El tokenizador correspondiente o None
    """
    try:
        if any(m in model_name.lower() for m in ['gpt', 'text-']):  # OpenAI
            try:
                return tiktoken.encoding_for_model(model_name)
            except KeyError:
                return tiktoken.get_encoding("cl100k_base")
        
        elif Anthropic and 'claude' in model_name.lower():  # Anthropic
            return Anthropic()
        
        elif AutoTokenizer and any(m in model_name.lower() for m in ['llama', 'mistral', 'gemma']):  # HF
            return AutoTokenizer.from_pretrained(model_name)
        
        elif genai and 'gemini' in model_name.lower():  # Google
            return genai
        
        return None  # Para usar estimación
    except Exception as e:
        log_message(f"Error al obtener tokenizador para {model_name}: {str(e)}", level='ERROR')
        return None

def contar_tokens(texto, modelo="gpt-3.5-turbo"):
    """
    Cuenta la cantidad de tokens en un texto para cualquier modelo de LLM
    
    IMPORTANTE: Esta función debe llamarse UNA SOLA VEZ para cada texto.
    El valor retornado debe guardarse y reutilizarse tanto para logs como
    para almacenamiento en base de datos, evitando recalcular los tokens.
    
    Args:
        texto (str): El texto para el cual contar tokens
        modelo (str): El modelo de LLM para el cual contar tokens
        
    Returns:
        int: La cantidad de tokens garantizada como entero
    """
    try:
        # Validar que texto sea string
        if texto is None:
            log_message("Error: texto es None", level='ERROR')
            return 0
        
        # Convertir a string si no lo es
        if not isinstance(texto, str):
            texto = str(texto)
            log_message(f"Advertencia: texto no es string, convertido a string: {type(texto)}", level='WARNING')
        
        # Obtener el tokenizador adecuado
        tokenizer = get_tokenizer(modelo)
        
        # Contar tokens según el tipo de tokenizador
        if isinstance(tokenizer, tiktoken.Encoding):  # OpenAI (tiktoken)
            tokens = len(tokenizer.encode(texto))
        elif tokenizer is not None and Anthropic is not None and isinstance(tokenizer, Anthropic):  # Anthropic
            tokens = tokenizer.count_tokens(texto)
        elif tokenizer is not None and hasattr(tokenizer, 'encode'):  # Hugging Face
            tokens = len(tokenizer.encode(texto))
        elif genai is not None and 'gemini' in modelo.lower():  # Google
            tokens = genai.count_token(texto)
        else:
            # Estimación para modelos desconocidos (1 token ~ 4 caracteres)
            # Es una aproximación razonable cuando no tenemos acceso al tokenizador específico
            tokens = max(len(texto) // 4, 1)  # Mínimo 1 token
            log_message(f"Usando estimación para modelo {modelo}: ~{tokens} tokens", level='WARNING')
        
        # Asegurar que el resultado sea entero
        return int(tokens)
        
    except Exception as e:
        log_message(f"Error al contar tokens: {str(e)}", level='ERROR')
        # Usar estimación como fallback en caso de error
        return max(len(texto) // 4, 1)

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
