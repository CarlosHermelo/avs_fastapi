# Consulta a Base de Datos Vectorial Qdrant

Este script permite consultar la base de datos vectorial Qdrant para buscar fragmentos relevantes a partir de un texto o pregunta.

## Requisitos previos

- Python 3.8 o superior
- Módulos de Python necesarios (instalables con pip):
  - langchain-openai
  - langchain-qdrant
  - qdrant-client
  - configparser

## Configuración

El script utiliza el archivo `config.ini` para obtener:
- La API key de OpenAI
- La URL de Qdrant (por defecto: http://localhost:6333)
- El nombre de la colección a consultar (por defecto: fragment_store)

## Uso del script

Para utilizar el script, simplemente ejecútalo con Python:

```
python consulta_qdrant.py
```

### Funcionamiento

1. El script se conecta a Qdrant usando la URL configurada
2. Verifica las colecciones disponibles
3. Te permite ingresar una pregunta o texto de consulta
4. Puedes especificar el número de resultados a mostrar
5. El script muestra los fragmentos más relevantes encontrados, con su contenido y metadatos

### Modo interactivo

El script funciona en modo interactivo, permitiéndote realizar múltiples consultas en una misma sesión.
Para salir del programa, simplemente escribe "salir" cuando te solicite una pregunta.

## Ejemplos de consultas

- "¿Cómo es la afiliación de la esposa de un afiliado?"
- "trámite para retirar bastón"
- "requisitos para solicitar silla de ruedas"

## Solución de problemas

Si encuentras problemas al ejecutar el script:

1. Verifica que Qdrant esté en funcionamiento en la URL configurada
2. Comprueba que la API key de OpenAI sea válida
3. Asegúrate de que la colección exista en Qdrant

Para debug más avanzado, utiliza el script `debug_qdrant.py` que muestra información detallada sobre la configuración y conectividad.

## Scripts adicionales

- `debug_qdrant.py`: Script de diagnóstico para verificar la conexión con Qdrant
- `buscar_fragmentos.py`: Versión alternativa con funcionalidades adicionales
- `test_qdrant.py`: Script simple para probar la conexión con Qdrant 