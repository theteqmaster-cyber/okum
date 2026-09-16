import os
import json
import urllib.request
import urllib.error
import threading
from PyQt6.QtCore import QThread, pyqtSignal

# --- ENV LOADER (Zero-dependency .env parser) ---
def load_env(env_path=None):
    """Loads key-value pairs from .env into os.environ if not already present."""
    if env_path is None:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass

# Load env on module import
load_env()

# Constants & Defaults
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_LOCAL_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "groq/compound")

def get_groq_api_key():
    load_env()
    return os.environ.get("GROQ_API_KEY", "").strip()

def preload_model(model=DEFAULT_LOCAL_MODEL):
    """Sends a background warmup request to load the local Ollama model into memory."""
    def _warmup():
        try:
            url = f"{OLLAMA_HOST}/api/generate"
            payload = json.dumps({
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": "24h"
            }).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as _:
                pass
        except Exception:
            pass

    thread = threading.Thread(target=_warmup, daemon=True)
    thread.start()

def unload_model(model=DEFAULT_LOCAL_MODEL):
    """Sends an immediate unload request to Ollama to free system memory."""
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = json.dumps({
            "model": model,
            "keep_alive": 0
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=3) as _:
            pass
    except Exception:
        pass

def is_ollama_running():
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

class AIQueryWorker(QThread):
    """
    Unified AI query worker supporting both:
    1. 'local' / 'ollama' - Local Ollama LLM
    2. 'groq' / 'online'  - Online Groq Cloud LLM (llama-3.3-70b-versatile)
    """
    response_ready = pyqtSignal(str, str, str)  # (response_text, session_id, prompt)
    error_occurred = pyqtSignal(str, str)       # (error_message, session_id)

    def __init__(self, prompt, session_id, provider="local", model=None, system_prompt=None):
        super().__init__()
        self.prompt = prompt
        self.session_id = session_id
        self.provider = (provider or "local").lower().strip()
        self.system_prompt = system_prompt or "You are Okum, a helpful, friendly, smart, and direct AI assistant for Linux. Keep answers clear, insightful, accurate, and concise."
        
        if self.provider in ("groq", "online"):
            self.model = model or DEFAULT_GROQ_MODEL
        else:
            self.model = model or DEFAULT_LOCAL_MODEL

    def run(self):
        if self.provider in ("groq", "online"):
            self._run_groq()
        else:
            self._run_ollama()

    def _run_ollama(self):
        try:
            url = f"{OLLAMA_HOST}/api/generate"
            payload_data = {
                "model": self.model,
                "prompt": self.prompt,
                "system": self.system_prompt,
                "stream": False,
                "keep_alive": "24h"
            }
            payload = json.dumps(payload_data).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=90) as response:
                result = json.loads(response.read().decode('utf-8'))
                answer = result.get('response', '').strip()
                self.response_ready.emit(answer, self.session_id, self.prompt)
        except urllib.error.URLError as e:
            self.error_occurred.emit(
                f"Could not connect to Local Ollama ({str(e.reason)}).\nMake sure Ollama is running (`ollama serve`), or switch to Online AI (Groq) from the dropdown above.",
                self.session_id
            )
        except Exception as e:
            self.error_occurred.emit(f"Local AI error: {str(e)}", self.session_id)

    def _run_groq(self):
        api_key = get_groq_api_key()
        if not api_key:
            self.error_occurred.emit("Groq API key not found in .env. Please configure GROQ_API_KEY.", self.session_id)
            return

        try:
            payload_data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            payload = json.dumps(payload_data).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Okum/1.0'
            }
            req = urllib.request.Request(GROQ_API_URL, data=payload, headers=headers)

            with urllib.request.urlopen(req, timeout=40) as response:
                result = json.loads(response.read().decode('utf-8'))
                choices = result.get('choices', [])
                if choices and 'message' in choices[0]:
                    answer = choices[0]['message'].get('content', '').strip()
                    self.response_ready.emit(answer, self.session_id, self.prompt)
                else:
                    self.error_occurred.emit("Empty response received from Groq API.", self.session_id)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode('utf-8')
                parsed_err = json.loads(err_body).get('error', {}).get('message', '')
                if parsed_err:
                    err_body = parsed_err
            except Exception:
                pass
            
            if e.code == 401:
                self.error_occurred.emit("Groq Authentication Failed: Invalid API Key in .env", self.session_id)
            elif e.code == 429:
                self.error_occurred.emit("Groq Rate Limit Reached: Please wait a moment before trying again.", self.session_id)
            else:
                self.error_occurred.emit(f"Groq API HTTP {e.code}: {err_body or e.reason}", self.session_id)
        except urllib.error.URLError as e:
            self.error_occurred.emit(f"Network error reaching Groq Cloud ({str(e.reason)}). Please check your internet connection.", self.session_id)
        except Exception as e:
            self.error_occurred.emit(f"Online AI error: {str(e)}", self.session_id)

# Backward-compatibility alias
OllamaQueryWorker = AIQueryWorker
