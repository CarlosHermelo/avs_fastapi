# app/services/token_utils.py
def count_words(text):
    return len(text.split())

def validar_palabras(prompt, max_palabras=10000):
    num_palabras = count_words(prompt)
    return (num_palabras <= max_palabras), num_palabras

def reducir_contenido_por_palabras(text, max_palabras=10000):
    palabras = text.split()
    if len(palabras) > max_palabras:
        return " ".join(palabras[:max_palabras]) + "\n\n[Contenido truncado...]"
    return text

import tiktoken

def contar_tokens(texto, modelo="gpt-3.5-turbo"):
    if modelo.startswith("gpt-4"):
        codificador = tiktoken.encoding_for_model("gpt-4")
    elif modelo.startswith("gpt-3.5"):
        codificador = tiktoken.encoding_for_model("gpt-3.5-turbo")
    else:
        codificador = tiktoken.get_encoding("cl100k_base")
    return len(codificador.encode(texto))
