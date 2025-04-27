# app/core/config.py
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

api_key = config['DEFAULT'].get('openai_api_key')
os.environ['OPENAI_API_KEY'] = api_key

collection_name_fragmento = config['DEFAULT'].get('collection_name_fragmento', fallback='fragment_store')
model_name = config['DEFAULT'].get('modelo')

fragment_store_directory = config['SERVICIOS_SIMAP'].get('FRAGMENT_STORE_DIR', fallback='/content/chroma_fragment_store')
max_results = config['SERVICIOS_SIMAP'].getint('max_results', fallback=4)
fecha_desde_pagina = config['SERVICIOS_SIMAP'].get('fecha_desde', fallback='2024-01-08')
fecha_hasta_pagina = config['SERVICIOS_SIMAP'].get('fecha_hasta', fallback='2024-12-10')
