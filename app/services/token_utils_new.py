# app/services/token_utils.py
import tiktoken
from app.core.logging_config import log_message
from functools import lru_cache

try:
