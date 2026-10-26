import os
import sys
import hashlib
import asyncio
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

try:
    import edge_tts
except ImportError:
    edge_tts = None

VOICE_CACHE_DIR = os.path.expanduser('~/.local/share/okum/voice_cache')
os.makedirs(VOICE_CACHE_DIR, exist_ok=True)

# Natural British / Commonwealth female neural voice
DEFAULT_FEMALE_VOICE = "en-GB-SoniaNeural"

# Common reaction phrases to ensure 0ms latency and 100% offline neural voice
STANDARD_REACTIONS = [
    "Got it",
    "Yes sir",
    "Playing previous track",
    "Playing next track",
    "Pausing music",
    "Resuming music",
    "Minimising tabs",
    "Shuffle on.",
    "Shuffle off.",
    "Shuffle on",
    "Shuffle off",
    "Cool",
    "Thinking",
    "I'm listening",
    "I'm sorry, I couldn't connect to the internet."
]

def _get_cache_filepath(text, voice=DEFAULT_FEMALE_VOICE):
    normalized = text.strip().lower()
    text_hash = hashlib.md5(f"{voice}:{normalized}".encode('utf-8')).hexdigest()
    return os.path.join(VOICE_CACHE_DIR, f"{text_hash}.mp3")

class TTSGenerateWorker(QThread):
    """Background worker that calls neural TTS API without blocking the Qt main loop."""
    generation_finished = pyqtSignal(str, str) # (text, audio_filepath)
    generation_failed = pyqtSignal(str, str)   # (text, error_msg)

    def __init__(self, text, voice=DEFAULT_FEMALE_VOICE, target_file=None):
        super().__init__()
        self.text = text
        self.voice = voice
        self.target_file = target_file or _get_cache_filepath(text, voice)

    def run(self):
        if not edge_tts:
            self.generation_failed.emit(self.text, "edge-tts package is not installed.")
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _generate():
                communicate = edge_tts.Communicate(self.text, self.voice)
                await communicate.save(self.target_file)

            loop.run_until_complete(_generate())
            loop.close()

            if os.path.exists(self.target_file) and os.path.getsize(self.target_file) > 0:
                self.generation_finished.emit(self.text, self.target_file)
            else:
                self.generation_failed.emit(self.text, "Generated audio file is empty or missing.")
        except Exception as e:
            self.generation_failed.emit(self.text, str(e))

class TTSService(QObject):
    """
    High-fidelity Neural Female Text-to-Speech Engine for Okum.
    - Uses Microsoft Azure neural voice (100% human-grade, zero robotic sound)
    - Caches common phrases locally for 0ms latency & offline reactions
    - Plays seamlessly via QMediaPlayer / fallback without blocking UI
    """
    started_speaking = pyqtSignal(str)
    finished_speaking = pyqtSignal(str)
    state_changed = pyqtSignal(str)  # 'idle', 'generating', 'speaking'

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TTSService()
        return cls._instance

    def __init__(self, voice=DEFAULT_FEMALE_VOICE):
        super().__init__()
        self.voice = voice
        self._current_text = None
        self._is_speaking = False
        self._play_process = None
        self._worker = None

        # Setup native Qt audio player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Fallback offline native speech-dispatcher if edge-tts fails and no cache exists
        try:
            from PyQt6.QtTextToSpeech import QTextToSpeech
            self._fallback_tts = QTextToSpeech()
            for v in self._fallback_tts.availableVoices():
                if 'female' in v.name().lower() or 'ann' in v.name().lower() or 'jenny' in v.name().lower():
                    self._fallback_tts.setVoice(v)
                    break
        except Exception:
            self._fallback_tts = None

        # Pre-cache common phrases in background if not already cached
        QTimer.singleShot(1500, self.preload_common_reactions)

    def preload_common_reactions(self):
        """Asynchronously pre-caches standard reaction phrases."""
        for phrase in STANDARD_REACTIONS:
            fp = _get_cache_filepath(phrase, self.voice)
            if not os.path.exists(fp) or os.path.getsize(fp) == 0:
                self._generate_async_to_cache(phrase)

    def _generate_async_to_cache(self, text):
        worker = TTSGenerateWorker(text, self.voice)
        worker.start()
        if not hasattr(self, '_background_workers'):
            self._background_workers = []
        self._background_workers.append(worker)

    def speak(self, text, priority=False, on_finish=None):
        """
        Speaks the given text using the natural female voice.
        If priority is True, cancels any current speech immediately.
        """
        if not text or not text.strip():
            return

        clean_text = text.strip()

        if priority and self._is_speaking:
            self.stop()

        cached_file = _get_cache_filepath(clean_text, self.voice)
        if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
            self._play_file(clean_text, cached_file, on_finish)
            return

        # Active generation workers tracking to prevent premature garbage collection
        if not hasattr(self, '_active_workers'):
            self._active_workers = set()

        # Not in cache: generate on-the-fly via worker
        self.state_changed.emit("generating")
        worker = TTSGenerateWorker(clean_text, self.voice, cached_file)
        self._active_workers.add(worker)

        def _on_generated(txt, audio_path):
            self._active_workers.discard(worker)
            self._play_file(txt, audio_path, on_finish)

        def _on_error(txt, err):
            self._active_workers.discard(worker)
            print(f"[TTSService] Warning: Neural generation failed ({err}).")
            if self._fallback_tts:
                self._is_speaking = True
                self.started_speaking.emit(txt)
                self.state_changed.emit("speaking")
                self._fallback_tts.say(txt)
                words = len(txt.split())
                duration_sec = max(1.5, words * 0.4)
                QTimer.singleShot(int(duration_sec * 1000), lambda: self._on_finish(txt, on_finish))
            else:
                self.state_changed.emit("idle")
                if on_finish:
                    on_finish()

        worker.generation_finished.connect(_on_generated)
        worker.generation_failed.connect(_on_error)
        worker.finished.connect(lambda: self._active_workers.discard(worker))
        worker.start()

    def _play_file(self, text, audio_path, on_finish=None):
        self._current_text = text
        self._current_callback = on_finish
        self._is_speaking = True
        self.started_speaking.emit(text)
        self.state_changed.emit("speaking")

        try:
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(audio_path))
            self.player.play()
        except Exception as e:
            print(f"[TTSService] QMediaPlayer error: {e}, attempting ffplay fallback.")
            self._play_with_ffplay(audio_path, text, on_finish)

    def _play_with_ffplay(self, audio_path, text, on_finish=None):
        try:
            self._play_process = subprocess.Popen(
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            QTimer.singleShot(2500, lambda: self._on_finish(text, on_finish))
        except Exception as e:
            print(f"[TTSService] ffplay error: {e}")
            self._on_finish(text, on_finish)

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState and self._is_speaking:
            self._on_finish(self._current_text, getattr(self, '_current_callback', None))

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._is_speaking:
            self._on_finish(self._current_text, getattr(self, '_current_callback', None))

    def _on_finish(self, text, callback=None):
        self._is_speaking = False
        self.state_changed.emit("idle")
        if text:
            self.finished_speaking.emit(text)
        if callback and callable(callback):
            try:
                callback()
            except Exception:
                pass

    def stop(self):
        """Immediately stops speech playback."""
        self._is_speaking = False
        if self.player:
            self.player.stop()
        if self._play_process and self._play_process.poll() is None:
            try:
                self._play_process.terminate()
            except Exception:
                pass
            self._play_process = None
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker = None
        self.state_changed.emit("idle")

    def is_speaking(self):
        return self._is_speaking
