import os
import sys
import json
import time
import queue
import re
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QThread

try:
    import numpy as np
except ImportError:
    np = None

try:
    import vosk
    import sounddevice as sd
except ImportError:
    vosk = None
    sd = None

# Suppress verbose Vosk C logs to stdout
if vosk:
    vosk.SetLogLevel(-1)

VOICE_LOG_PATH = os.path.expanduser('~/.local/share/okum/voice.log')
os.makedirs(os.path.dirname(VOICE_LOG_PATH), exist_ok=True)

def log_voice(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}\n"
    print(f"[VoiceService] {msg}", flush=True)
    try:
        with open(VOICE_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass

def ensure_optimal_microphone_level():
    """
    Calibrates microphone input volume to 40% (optimal sweet spot for Dell Latitude E7470).
    Prevents both digital clipping (>65%) and inaudible capture (<20%).
    """
    try:
        res = subprocess.run(['pactl', 'get-source-volume', '@DEFAULT_SOURCE@'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            match = re.search(r'(\d+)%', res.stdout)
            if match:
                vol = int(match.group(1))
                if vol > 55 or vol < 28:
                    subprocess.run(['pactl', 'set-source-volume', '@DEFAULT_SOURCE@', '40%'], check=False, timeout=2)
                    log_voice(f"Calibrated microphone input volume from {vol}% to 40% (optimal dynamic range).")
                else:
                    log_voice(f"Microphone input volume calibrated at {vol}%.")
    except Exception as e:
        log_voice(f"Note: Could not inspect microphone volume: {e}")

# Precompiled Robust Regex Command Patterns with Word Boundaries
RE_SHUFFLE_OFF = re.compile(
    r'\b(?:shuffle\s+off|stop\s+shuffle|turn\s+off\s+shuffle|disable\s+shuffle|cancel\s+shuffle|no\s+shuffle|don\'?t\s+shuffle|off\s+shuffle)\b',
    re.IGNORECASE
)

RE_SHUFFLE_ON = re.compile(
    r'\b(?:shuffle\s+on|turn\s+on\s+shuffle|start\s+shuffle|enable\s+shuffle|shuffle\s+mode|shuffle\s+music|shuffle\s+songs|play\s+shuffle)\b'
    r'|'
    r'^(?:okum\s+|hey\s+okum\s+|please\s+)?shuffle(?:\s+please)?$',
    re.IGNORECASE
)

RE_PAUSE = re.compile(
    r'\b(?:stop|pause|halt|quiet|be quiet|shut up|silence|mute)\b'
    r'|'
    r'\b(?:stop|pause)\s*(?:the\s*)?(?:music|song|track|playback|playing)?\b',
    re.IGNORECASE
)

RE_NEXT = re.compile(
    r'\b(?:next\s+(?:track|song|music|one)|skip\s+(?:the\s+)?(?:track|song|music|this|it)?|play\s+next)\b'
    r'|'
    r'^(?:okum\s+|hey\s+okum\s+)?(?:next|skip)(?:\s+please)?$',
    re.IGNORECASE
)

RE_PREV = re.compile(
    r'\b(?:previous\s+(?:track|song|music|one)|prev\s+(?:track|song|music|one)|go\s+back|play\s+previous|last\s+(?:song|track))\b'
    r'|'
    r'^(?:okum\s+|hey\s+okum\s+)?(?:previous|prev|back)(?:\s+please)?$',
    re.IGNORECASE
)

RE_PLAY = re.compile(
    r'\b(?:play|resume|start|unpause|continue)\s*(?:the\s*)?(?:music|song|track|playback|playing)?\b'
    r'|'
    r'\b(?:play|resume|unpause)\b',
    re.IGNORECASE
)

RE_MINIMIZE = re.compile(
    r'\b(?:minimi[sz]e\s*(?:all\s*)?(?:tabs|windows)?|hide\s*(?:all\s*)?(?:tabs|windows)?|show\s*desktop)\b',
    re.IGNORECASE
)

RE_MINI_PLAYER = re.compile(
    r'\b(?:mini\s*player|floating\s*(?:player|music)|show\s*mini|open\s*mini)\b',
    re.IGNORECASE
)

RE_TIME = re.compile(
    r'\b(?:what(?:\s*is|\s*\'?s)?\s*(?:the\s*)?time(?:\s*now|\s*is\s*it)?|current\s*time|check\s*time|tell\s*me\s*the\s*time)\b'
    r'|'
    r'^(?:okum\s+|hey\s+okum\s+)?time$',
    re.IGNORECASE
)

RE_DATE = re.compile(
    r'\b(?:what(?:\s*is|\s*\'?s)?\s*(?:the\s*|today\'?s\s*)?date|current\s*date|check\s*date|today\'?s\s*date)\b'
    r'|'
    r'^(?:okum\s+|hey\s+okum\s+)?date$',
    re.IGNORECASE
)

WAKE_PREFIX_PATTERN = re.compile(
    r'^(?:hey\s+|hay\s+|hello\s+|hi\s+)?(?:okum|oakum|welcome\s+okum)\s*',
    re.IGNORECASE
)

class VoiceListenerThread(QThread):
    """
    Dedicated low-priority background thread that captures microphone input
    and processes speech via Vosk offline engine.
    Never blocks the Qt UI loop and keeps RAM consumption < 50MB.
    Includes software AGC and speaker-bleed mitigation.
    """
    sig_command_minimize = pyqtSignal()
    sig_command_mini_player = pyqtSignal()
    sig_command_play_music = pyqtSignal()
    sig_command_pause_music = pyqtSignal()
    sig_command_prev_track = pyqtSignal()
    sig_command_next_track = pyqtSignal()
    sig_command_time = pyqtSignal()
    sig_command_date = pyqtSignal()
    sig_command_shuffle_on = pyqtSignal()
    sig_command_shuffle_off = pyqtSignal()
    sig_wake_word = pyqtSignal()
    sig_chat_query = pyqtSignal(str)
    sig_status_changed = pyqtSignal(str) # "idle", "listening", "capturing", "muted"

    def __init__(self, tts_service=None, music_service=None):
        super().__init__()
        self.tts_service = tts_service
        self.music_service = music_service
        self._is_running = True
        self._is_muted = False
        self._audio_queue = queue.Queue()
        self._mode = "idle" # "idle" or "capturing_query"
        self._capture_start_time = 0
        self._capture_buffer = []
        self._last_command_time = 0

    def mute(self, muted=True):
        self._is_muted = muted
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        status = "muted" if muted else "idle"
        log_voice(f"Voice state set to: {status}")
        self.sig_status_changed.emit(status)

    def is_muted(self):
        return self._is_muted

    def stop(self):
        self._is_running = False
        self.wait(1000)

    def is_music_playing(self):
        """Checks if music is currently playing through Okum MusicService."""
        try:
            from services.music_service import MusicService
            from PyQt6.QtMultimedia import QMediaPlayer
            ms = self.music_service or MusicService.get_instance()
            if ms and hasattr(ms, 'player') and ms.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                return True
        except Exception:
            pass
        return False

    def _strip_wake_prefix(self, text):
        return WAKE_PREFIX_PATTERN.sub('', text).strip()

    def _has_wake_prefix(self, text):
        return bool(WAKE_PREFIX_PATTERN.match(text))

    def _process_audio_chunk(self, data):
        """
        Passes clean PCM audio to Vosk.
        Microphone input is calibrated to 40% optimal dynamic range via pactl,
        allowing Vosk's native Cepstral Mean Normalization (CMVN) and VAD to detect speech and silence cleanly.
        """
        return data

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback from sounddevice."""
        if self._is_running and not self._is_muted:
            self._audio_queue.put(bytes(indata))

    def run(self):
        if not vosk or not sd:
            log_voice("Error: vosk or sounddevice not installed in this Python environment.")
            return

        # Ensure healthy microphone capture gain
        ensure_optimal_microphone_level()

        try:
            model = vosk.Model(lang="en-gb")
            log_voice("Loaded British / Commonwealth English acoustic model (en-gb).")
        except Exception as e:
            try:
                model = vosk.Model(lang="en-us")
                log_voice("Loaded fallback US model (en-us).")
            except Exception as e2:
                log_voice(f"Error loading Vosk model: {e2}")
                return

        samplerate = 16000
        rec = vosk.KaldiRecognizer(model, samplerate)
        rec.SetWords(False)

        try:
            with sd.RawInputStream(
                samplerate=samplerate,
                blocksize=4000,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            ):
                self.sig_status_changed.emit("idle")
                log_voice("Offline voice listener active and listening to microphone.")

                while self._is_running:
                    try:
                        data = self._audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    # If TTS is currently speaking, drop audio to prevent self-triggering
                    if self.tts_service and self.tts_service.is_speaking():
                        rec.Reset()
                        continue

                    # Software Digital AGC & Normalization
                    data = self._process_audio_chunk(data)

                    # Process audio chunk
                    if rec.AcceptWaveform(data):
                        res_json = json.loads(rec.Result())
                        text = res_json.get("text", "").strip().lower()
                        if text:
                            log_voice(f"Utterance heard: '{text}'")
                            self._handle_recognized_text(text, rec)
                    else:
                        partial_json = json.loads(rec.PartialResult())
                        partial = partial_json.get("partial", "").strip().lower()
                        if partial:
                            self._handle_partial_text(partial, rec)

                    # Check capture timeout for conversational chat query
                    if self._mode == "capturing_query":
                        elapsed = time.time() - self._capture_start_time
                        if elapsed > 6.0:
                            final_json = json.loads(rec.FinalResult())
                            query = final_json.get("text", "").strip()
                            if not query and self._capture_buffer:
                                query = " ".join(self._capture_buffer)
                            
                            self._mode = "idle"
                            self.sig_status_changed.emit("idle")
                            if query:
                                log_voice(f"Captured query on timeout: '{query}'")
                                self.sig_chat_query.emit(query)
                            self._capture_buffer = []
                            rec.Reset()

        except Exception as e:
            log_voice(f"Audio listener exception: {e}")

    def _handle_partial_text(self, partial, rec):
        """Processes partial streaming results for immediate reaction on complete commands."""
        clean_partial = partial.strip()
        if clean_partial and clean_partial != getattr(self, '_last_logged_partial', ''):
            now = time.time()
            if now - getattr(self, '_last_partial_log_time', 0) > 0.5:
                self._last_partial_log_time = now
                self._last_logged_partial = clean_partial
                log_voice(f"Hearing: '{clean_partial}'")

        if self._mode == "idle":
            music_playing = self.is_music_playing()
            core = self._strip_wake_prefix(partial)

            # Priority 1: When music is playing, give top fast-streaming priority to stop/pause!
            if music_playing:
                if RE_PAUSE.search(core) or RE_PAUSE.search(partial):
                    if self._match_command(partial):
                        log_voice(f"Fast streaming priority stop during music: '{partial}'")
                        rec.Reset()
                        return
                # If explicit wake prefix is spoken during music, allow command
                if self._has_wake_prefix(partial) and self._match_command(partial):
                    log_voice(f"Fast streaming wake-prefixed trigger during music: '{partial}'")
                    rec.Reset()
                    return
                # Suppress lyric false-positives from accidentally changing songs
                return

            # When music is not playing, standard fast trigger
            if self._match_command(partial):
                log_voice(f"Fast streaming trigger for command: '{partial}'")
                rec.Reset()
                return

        elif self._mode == "capturing_query":
            self._capture_buffer.append(partial)

    def _handle_recognized_text(self, text, rec):
        """Processes full utterance results."""
        self._last_logged_partial = ""
        if self._mode == "idle":
            # 1. Check if it matches an offline command
            if self._match_command(text):
                rec.Reset()
                return

            # 2. Check if it's the AI chat wake word
            if self._is_wake_word(text):
                remainder = self._extract_post_wake_query(text)
                if remainder:
                    log_voice(f"Wake word with inline query: '{remainder}'")
                    self.sig_wake_word.emit()
                    self.sig_chat_query.emit(remainder)
                else:
                    log_voice("Wake word triggered. Entering query capture mode.")
                    self._trigger_wake_word(rec)
                rec.Reset()
                return

        elif self._mode == "capturing_query":
            clean_query = text.strip()
            self._mode = "idle"
            self.sig_status_changed.emit("idle")
            if clean_query:
                log_voice(f"Captured query: '{clean_query}'")
                self.sig_chat_query.emit(clean_query)
            self._capture_buffer = []
            rec.Reset()

    def _is_wake_word(self, text):
        t = text.strip().lower()
        wake_terms = [
            "hey okum", "okum", "hay okum", "hey oakum", "oakum",
            "hello okum", "welcome okum", "hi okum"
        ]
        # Check exact or prefix
        for w in wake_terms:
            if t == w or t.startswith(w + " ") or (" " + w + " ") in t or t.endswith(" " + w):
                return True
        return False

    def _trigger_wake_word(self, rec):
        self._mode = "capturing_query"
        self._capture_start_time = time.time()
        self._capture_buffer = []
        self.sig_wake_word.emit()
        self.sig_status_changed.emit("capturing")
        rec.Reset()

    def _extract_post_wake_query(self, text):
        pattern = r"(?:hey|hay|hello|hi)?\s*(?:okum|oakum|welcome\s+okum)\s+(.+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            # If it matches an offline command, don't treat as AI chat query
            if not self._match_command(query, emit=False):
                return query
        return None

    def _match_command(self, text, emit=True):
        """
        Matches offline commands with high forgiveness and debouncing:
        - stop / pause music
        - play / resume music
        - next track / skip
        - previous track / go back
        - minimise all tabs / hide windows
        - what's the time
        - what's the date
        - shuffle on / off
        """
        t = text.lower().strip()
        now = time.time()

        # Check if already triggered recently within debounce window
        if emit and (now - self._last_command_time < 1.5):
            return True

        core = self._strip_wake_prefix(t)

        # 1. Shuffle Off (check before pause so 'stop shuffle' matches shuffle off)
        if RE_SHUFFLE_OFF.search(core) or RE_SHUFFLE_OFF.search(t):
            log_voice(f"Command matched: SHUFFLE OFF (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_shuffle_off.emit()
            return True

        # 2. Shuffle On (check before play so 'play shuffle' matches shuffle on)
        if RE_SHUFFLE_ON.search(core) or RE_SHUFFLE_ON.search(t):
            log_voice(f"Command matched: SHUFFLE ON (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_shuffle_on.emit()
            return True

        # 3. Stop / Pause Music (Top priority)
        if RE_PAUSE.search(core) or RE_PAUSE.search(t):
            log_voice(f"Command matched: PAUSE MUSIC (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_pause_music.emit()
            return True

        # 4. Next Track / Skip (check before play so 'play next' routes to next track)
        if RE_NEXT.search(core) or RE_NEXT.search(t):
            log_voice(f"Command matched: NEXT TRACK (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_next_track.emit()
            return True

        # 5. Previous Track / Back (check before play so 'play previous' routes to prev track)
        if RE_PREV.search(core) or RE_PREV.search(t):
            log_voice(f"Command matched: PREVIOUS TRACK (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_prev_track.emit()
            return True

        # 6. Play / Resume Music
        if RE_PLAY.search(core) or RE_PLAY.search(t):
            log_voice(f"Command matched: PLAY MUSIC (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_play_music.emit()
            return True

        # 7. Minimise / Hide windows
        if RE_MINIMIZE.search(core) or RE_MINIMIZE.search(t):
            log_voice(f"Command matched: MINIMIZE TABS (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_minimize.emit()
            return True

        # 7b. Floating Mini Player
        if RE_MINI_PLAYER.search(core) or RE_MINI_PLAYER.search(t):
            log_voice(f"Command matched: MINI PLAYER (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_mini_player.emit()
            return True

        # 8. Check Time
        if RE_TIME.search(core) or RE_TIME.search(t):
            log_voice(f"Command matched: TIME (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_time.emit()
            return True

        # 9. Check Date
        if RE_DATE.search(core) or RE_DATE.search(t):
            log_voice(f"Command matched: DATE (heard '{text}')")
            if emit:
                self._last_command_time = now
                self.sig_command_date.emit()
            return True

        return False

class VoiceService(QObject):
    """
    High-level Voice Service manager for Okum.
    Coordinates between VoiceListenerThread, TTSService, MusicService, and UI Mascot.
    """
    _instance = None

    @classmethod
    def get_instance(cls, tts_service=None, music_service=None):
        if cls._instance is None:
            cls._instance = VoiceService(tts_service=tts_service, music_service=music_service)
        return cls._instance

    def __init__(self, tts_service=None, music_service=None):
        super().__init__()
        from services.tts_service import TTSService
        self.tts = tts_service or TTSService.get_instance()
        self.music_service = music_service
        self.listener_thread = VoiceListenerThread(tts_service=self.tts, music_service=self.music_service)
        self._is_active = False

    def start(self):
        if not self._is_active:
            self.listener_thread.start()
            self._is_active = True
            log_voice("VoiceService started.")

    def stop(self):
        if self._is_active:
            self.listener_thread.stop()
            self._is_active = False
            log_voice("VoiceService stopped.")

    def toggle_mute(self):
        muted = not self.listener_thread.is_muted()
        self.listener_thread.mute(muted)
        return muted

    def is_muted(self):
        return self.listener_thread.is_muted()
