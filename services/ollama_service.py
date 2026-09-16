"""
Compatibility shim for ollama_service.
Ollama has been retired in favor of Groq Cloud AI.
"""
from services.ai_service import (
    preload_model,
    unload_model,
    is_ollama_running,
    AIQueryWorker,
    OllamaQueryWorker,
)

__all__ = [
    'preload_model',
    'unload_model',
    'is_ollama_running',
    'AIQueryWorker',
    'OllamaQueryWorker',
]
