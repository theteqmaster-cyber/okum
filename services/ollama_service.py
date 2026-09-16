"""
Compatibility layer for ollama_service.
Delegates to unified services.ai_service which supports both Local (Ollama) and Online (Groq).
"""
from services.ai_service import (
    OLLAMA_HOST,
    DEFAULT_LOCAL_MODEL as DEFAULT_MODEL,
    preload_model,
    unload_model,
    is_ollama_running,
    AIQueryWorker,
    OllamaQueryWorker,
    get_groq_api_key,
    load_env
)

