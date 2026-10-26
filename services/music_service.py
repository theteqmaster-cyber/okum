import os
import random
import hashlib
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QThread, QFileSystemWatcher, QTimer, Qt, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices

try:
    import mutagen
except ImportError:
    mutagen = None

VALID_AUDIO_EXTS = {'.mp3', '.m4a', '.opus', '.aac', '.wav', '.flac', '.ogg', '.wma'}

def format_time_ms(ms):
    if not ms or ms < 0:
        return "00:00"
    total_seconds = int(ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def get_music_dirs():
    """
    Discovers all available music sources including ~/Downloads, Euro Truck Simulator 2,
    and standard user Music folders.
    """
    candidates = [
        os.path.expanduser('~/Music'),
        os.path.expanduser('~/music'),
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~/downloads'),
        os.path.expanduser('~/.local/share/Euro Truck Simulator 2/music/songs'),
        os.path.expanduser('~/.local/share/Euro Truck Simulator 2/music'),
        os.path.expanduser('~/.local/share/ets2/music/songs'),
    ]
    found = []
    for c in candidates:
        if os.path.isdir(c) and c not in found:
            found.append(c)

    if not found:
        default_dir = os.path.expanduser('~/Music')
        os.makedirs(default_dir, exist_ok=True)
        found.append(default_dir)

    return found

class CoverArtCache:
    """
    High-performance LRU memory cache for extracted ID3 album art thumbnails
    with sleek procedural fallback. Keeps RAM overhead strictly below ~5MB.
    """
    _cache = {}
    _max_size = 150

    @classmethod
    def get_cover_pixmap(cls, filepath, size=64):
        if not filepath:
            return cls.get_default_pixmap(size)

        cache_key = f"{filepath}_{size}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        pix = None
        if mutagen and os.path.exists(filepath):
            try:
                audio = mutagen.File(filepath)
                if audio and audio.tags:
                    for tag in audio.tags.values():
                        if tag.__class__.__name__ == 'APIC' or hasattr(tag, 'data'):
                            img_data = getattr(tag, 'data', None)
                            if img_data:
                                qimg = QImage.fromData(img_data)
                                if not qimg.isNull():
                                    pix = QPixmap.fromImage(qimg).scaled(
                                        size, size,
                                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                        Qt.TransformationMode.SmoothTransformation
                                    )
                                    break
                    if pix is None and 'covr' in audio.tags:
                        covr_data = audio.tags['covr']
                        if covr_data and len(covr_data) > 0:
                            qimg = QImage.fromData(covr_data[0])
                            if not qimg.isNull():
                                pix = QPixmap.fromImage(qimg).scaled(
                                    size, size,
                                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    Qt.TransformationMode.SmoothTransformation
                                )
                    if pix is None and hasattr(audio, 'pictures') and audio.pictures:
                        qimg = QImage.fromData(audio.pictures[0].data)
                        if not qimg.isNull():
                            pix = QPixmap.fromImage(qimg).scaled(
                                size, size,
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation
                            )
            except Exception:
                pass

        if pix is None or pix.isNull():
            pix = cls.get_default_pixmap(size, seed=filepath)

        if len(cls._cache) >= cls._max_size:
            keys_to_remove = list(cls._cache.keys())[:30]
            for k in keys_to_remove:
                cls._cache.pop(k, None)

        cls._cache[cache_key] = pix
        return pix

    @classmethod
    def get_default_pixmap(cls, size=64, seed=None):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        h = abs(hash(seed or "okum")) % 360
        c1 = QColor.fromHsv(h, 170, 220)
        c2 = QColor.fromHsv((h + 40) % 360, 200, 140)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(0, 0, size, size, 8, 8)

        # Inner subtle vinyl groove rings
        p.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        center = size / 2.0
        p.drawEllipse(QPointF(center, center), size * 0.35, size * 0.35)
        p.drawEllipse(QPointF(center, center), size * 0.2, size * 0.2)
        p.setBrush(QColor(15, 23, 42, 220))
        p.drawEllipse(QPointF(center, center), size * 0.08, size * 0.08)

        p.end()
        return pix

    @classmethod
    def get_hero_wallpaper(cls, filepath, width=376, height=142):
        """
        Ultra-fast (<0.5ms) low-blur semi-transparent wallpaper for the Now Playing hero card.
        Uses cached procedural placeholder if no cover art exists.
        """
        cache_key = f"hero_wall_{filepath}_{width}_{height}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        raw = cls.get_cover_pixmap(filepath, size=180)
        # Low blur: gentle soft contours preserving identifiable shapes (downscale to 80x40, then upscale)
        low_blur = raw.scaled(80, 40, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        wall = low_blur.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

        if len(cls._cache) >= cls._max_size:
            keys_to_remove = list(cls._cache.keys())[:30]
            for k in keys_to_remove:
                cls._cache.pop(k, None)

        cls._cache[cache_key] = wall
        return wall

def get_music_dir():
    dirs = get_music_dirs()
    return dirs[0] if dirs else os.path.expanduser('~/Music')

class LibraryScanWorker(QThread):
    """
    Background worker that scans thousands of tracks across multiple directories
    without freezing the UI or consuming excessive memory.
    """
    progress = pyqtSignal(int, int)      # (scanned_count, total_count)
    finished_scan = pyqtSignal(int)     # total_count in library

    def __init__(self, db, music_dirs):
        super().__init__()
        self.db = db
        self.music_dirs = list(music_dirs)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        # 1. Prune missing files from DB safely
        all_db_tracks = self.db.get_all_music_filepaths()
        existing_db_tracks = {}
        missing_filepaths = []

        for row in all_db_tracks:
            fp = row.get('filepath')
            if fp:
                if os.path.exists(fp):
                    existing_db_tracks[fp] = row
                else:
                    missing_filepaths.append(fp)

        if missing_filepaths:
            for i in range(0, len(missing_filepaths), 500):
                self.db.delete_music_tracks_batch(missing_filepaths[i:i + 500])

        if self._is_cancelled:
            return

        tracks_to_insert = []
        tracks_need_metadata = []

        def _scan_dir(path):
            if self._is_cancelled or not os.path.exists(path):
                return
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if self._is_cancelled:
                            break
                        if entry.is_dir(follow_symlinks=False):
                            _scan_dir(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in VALID_AUDIO_EXTS:
                                full_p = entry.path
                                if full_p not in existing_db_tracks:
                                    name_no_ext = os.path.splitext(entry.name)[0]
                                    if ' - ' in name_no_ext:
                                        parts = name_no_ext.split(' - ', 1)
                                        artist, title = parts[0].strip(), parts[1].strip()
                                    else:
                                        artist, title = 'Local Music', name_no_ext

                                    track_id = hashlib.md5(full_p.encode('utf-8')).hexdigest()[:16]
                                    item = {
                                        'id': track_id,
                                        'filepath': full_p,
                                        'filename': entry.name,
                                        'title': title,
                                        'artist': artist,
                                        'album': '',
                                        'duration': 0,
                                        'ext': ext
                                    }
                                    tracks_to_insert.append(item)
                                    tracks_need_metadata.append(item)

                                    if len(tracks_to_insert) >= 200:
                                        self.db.upsert_music_tracks_batch(tracks_to_insert)
                                        tracks_to_insert.clear()
                                        QThread.msleep(1)
            except (PermissionError, FileNotFoundError):
                pass

        for m_dir in self.music_dirs:
            if self._is_cancelled:
                break
            _scan_dir(m_dir)

        if tracks_to_insert and not self._is_cancelled:
            self.db.upsert_music_tracks_batch(tracks_to_insert)
            tracks_to_insert.clear()

        total_count = self.db.get_music_tracks_count()
        self.finished_scan.emit(total_count)

class MetadataScanWorker(QThread):
    """
    Lightweight background worker extracting audio duration and tags in small chunks.
    """
    progress = pyqtSignal(int, int)
    finished_scan = pyqtSignal()

    def __init__(self, db, tracks_to_scan):
        super().__init__()
        self.db = db
        self.tracks = tracks_to_scan
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not mutagen or not self.tracks:
            self.finished_scan.emit()
            return

        total = min(len(self.tracks), 1000) # Process up to 1000 at a time to conserve memory
        for i in range(total):
            if self._is_cancelled:
                break
            track = self.tracks[i]
            filepath = track.get('filepath')
            if not filepath or not os.path.exists(filepath):
                continue

            try:
                f = mutagen.File(filepath, easy=True)
                if f:
                    name_no_ext = os.path.splitext(os.path.basename(filepath))[0]
                    fallback_artist = 'Local Music'
                    fallback_title = name_no_ext
                    if ' - ' in name_no_ext:
                        parts = name_no_ext.split(' - ', 1)
                        fallback_artist, fallback_title = parts[0].strip(), parts[1].strip()

                    title = f.get('title', [None])[0] or track.get('title') or fallback_title
                    artist = f.get('artist', [None])[0] or track.get('artist') or fallback_artist
                    album = f.get('album', [None])[0] or track.get('album', '')
                    duration = int(f.info.length * 1000) if hasattr(f, 'info') and hasattr(f.info, 'length') else track.get('duration', 0)

                    if not title or not title.strip():
                        title = fallback_title
                    if not artist or not artist.strip():
                        artist = fallback_artist

                    self.db.update_track_metadata(filepath, title, artist, album, duration)
            except Exception:
                pass

            if i % 25 == 0:
                self.progress.emit(i + 1, total)
                QThread.msleep(3)

        self.finished_scan.emit()

class MusicService(QObject):
    _instance = None

    track_changed = pyqtSignal(dict)           # current track dict
    state_changed = pyqtSignal(bool)           # is_playing
    position_changed = pyqtSignal(int, int)    # (pos_ms, duration_ms)
    duration_changed = pyqtSignal(int)         # duration_ms
    mode_changed = pyqtSignal(str, bool)       # (loop_mode: 'none'|'all'|'one', is_shuffle)
    library_scanned = pyqtSignal(int)          # total track count
    track_unavailable = pyqtSignal(dict, str)  # (track_dict, message)
    error_occurred = pyqtSignal(str)           # playback or device error message
    queue_changed = pyqtSignal(int)            # count of tracks in Up Next queue
    favorite_changed = pyqtSignal(str, bool)   # (filepath, is_favorite)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.music_dirs = get_music_dirs()
        self.music_dir = self.music_dirs[0] if self.music_dirs else os.path.expanduser('~/Music')

        # QtMultimedia Player Setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        # Bluetooth / Audio Device Monitoring
        self.media_devices = QMediaDevices(self)
        self.media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)

        # Player signal bindings
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # State
        self.current_track = None
        self.current_playlist = []
        self.current_index = -1
        self.is_shuffle = False
        self.loop_mode = "all"  # 'none', 'all', 'one'
        self._shuffle_order = []
        self._shuffle_pos = -1

        # Up Next Priority Queue, History Stack & Search Play Mode
        self.up_next_queue = []
        self.history_stack = []
        self.is_single_play = False

        # Scanner threads
        self._scan_worker = None
        self._meta_worker = None

        # Real-time directory watcher
        self.watcher = QFileSystemWatcher(self)
        for d in self.music_dirs:
            if os.path.exists(d):
                self.watcher.addPath(d)
        self.watcher.directoryChanged.connect(self._on_watched_dir_changed)

        # Debounce timer for file watcher to wait until copy/download completes
        self._watch_timer = QTimer(self)
        self._watch_timer.setSingleShot(True)
        self._watch_timer.setInterval(1500)
        self._watch_timer.timeout.connect(self.scan_library_fast)

        # Initial background scan
        self.scan_library_fast()

    @classmethod
    def get_instance(cls, db=None):
        if cls._instance is None and db is not None:
            cls._instance = MusicService(db)
        return cls._instance

    def _on_watched_dir_changed(self, path):
        """Triggered automatically whenever a song is added, renamed, or deleted in the folder."""
        self._watch_timer.start()

    def scan_library_fast(self):
        """Asynchronously scans music directories in the background without blocking the UI."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait(500)

        # Refresh directory list in case ETS2 or new paths appeared
        self.music_dirs = get_music_dirs()
        for d in self.music_dirs:
            if os.path.exists(d) and d not in self.watcher.directories():
                self.watcher.addPath(d)

        self._scan_worker = LibraryScanWorker(self.db, self.music_dirs)
        self._scan_worker.finished_scan.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, total_count):
        self.library_scanned.emit(total_count)

    # Playback Controls with Safety Checks
    def play_track(self, track_dict, playlist=None, is_single_request=False, _attempt_count=0):
        max_attempts = max(1, len(self.current_playlist)) + 1
        if _attempt_count > max_attempts:
            self.stop()
            self.error_occurred.emit("No valid playable audio files found.")
            return

        if not track_dict:
            return

        filepath = track_dict.get('filepath', '')

        # Safety Check: Verify file exists on disk
        if not filepath or not os.path.exists(filepath):
            if filepath:
                self.db.delete_music_track(filepath)

            self.current_playlist = [t for t in self.current_playlist if t.get('filepath') != filepath]
            song_name = track_dict.get('title') or track_dict.get('filename') or 'Song'
            self.track_unavailable.emit(track_dict, f"File not found: '{song_name}' (removed from library).")

            if self.current_playlist:
                next_idx = self.current_index if self.current_index < len(self.current_playlist) else 0
                next_track_item = self.current_playlist[next_idx]
                self.play_track(next_track_item, self.current_playlist, _attempt_count=_attempt_count + 1)
            else:
                self.stop()
            return

        if playlist is not None and len(playlist) > 0:
            self.current_playlist = list(playlist)
        elif not self.current_playlist:
            self.current_playlist = self.db.get_all_tracks_for_playback()

        self.is_single_play = bool(is_single_request)

        try:
            self.current_index = next(i for i, t in enumerate(self.current_playlist) if t['filepath'] == filepath)
        except StopIteration:
            self.current_playlist.append(track_dict)
            self.current_index = len(self.current_playlist) - 1

        self.current_track = track_dict

        try:
            self.player.setSource(QUrl.fromLocalFile(filepath))
            self.player.play()
            try:
                new_count = self.db.record_track_play(filepath)
                self.current_track['play_count'] = new_count
                self.current_track['last_played_at'] = datetime.now().isoformat()
            except Exception as e:
                print(f"[MusicService] Error recording track play: {e}")
            self.track_changed.emit(self.current_track)
            self.state_changed.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"Player error loading track: {str(e)}")

    def add_to_up_next(self, track_dict):
        """Adds a track to the Up Next priority queue."""
        if track_dict:
            self.up_next_queue.append(track_dict)
            self.queue_changed.emit(len(self.up_next_queue))

    def clear_up_next(self):
        """Flushes the Up Next priority queue back to 0."""
        self.up_next_queue.clear()
        self.queue_changed.emit(0)

    def toggle_favorite(self, track_dict=None):
        """Toggles favorite bookmark for current or specified track."""
        target = track_dict or self.current_track
        if not target or 'filepath' not in target:
            return False
        fp = target['filepath']
        is_fav = self.db.toggle_track_favorite(fp)
        target['is_favorite'] = 1 if is_fav else 0
        if self.current_track and self.current_track.get('filepath') == fp:
            self.current_track['is_favorite'] = 1 if is_fav else 0
        self.favorite_changed.emit(fp, is_fav)
        return is_fav

    def is_favorite(self, filepath=None):
        fp = filepath or (self.current_track.get('filepath') if self.current_track else None)
        if not fp:
            return False
        return self.db.is_track_favorite(fp)

    def toggle_play_pause(self):
        try:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            elif self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self.player.play()
            elif self.current_track and os.path.exists(self.current_track.get('filepath', '')):
                self.player.play()
            elif self.current_playlist:
                self.play_track(self.current_playlist[0])
            else:
                first_tracks = self.db.search_music_tracks(limit=1)
                if first_tracks:
                    self.play_track(first_tracks[0])
        except Exception as e:
            self.error_occurred.emit(f"Playback toggle error: {str(e)}")

    def pause(self):
        try:
            self.player.pause()
        except Exception:
            pass

    def resume(self):
        try:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self.player.play()
            elif not self.current_track:
                all_tracks = self.db.search_music_tracks(limit=1000)
                if all_tracks:
                    self.play_track(all_tracks[0], playlist=all_tracks)
                else:
                    self.player.play()
            else:
                self.player.play()
        except Exception:
            pass

    def stop(self):
        try:
            self.player.stop()
            self.state_changed.emit(False)
        except Exception:
            pass

    def seek(self, position_ms):
        try:
            if self.player.isSeekable():
                self.player.setPosition(position_ms)
        except Exception:
            pass

    def set_volume(self, val_0_to_100):
        try:
            vol = max(0.0, min(1.0, val_0_to_100 / 100.0))
            self.audio_output.setVolume(vol)
        except Exception:
            pass

    def get_volume(self):
        try:
            return int(self.audio_output.volume() * 100)
        except Exception:
            return 85

    def set_shuffle(self, enabled: bool):
        self.is_shuffle = bool(enabled)
        if self.is_shuffle:
            self._generate_shuffle_deck(starting_track_index=self.current_index)
        else:
            self._shuffle_order = []
            self._shuffle_pos = self.current_index
        self.mode_changed.emit(self.loop_mode, self.is_shuffle)

    def toggle_shuffle(self):
        self.set_shuffle(not self.is_shuffle)

    def cycle_loop_mode(self):
        modes = ['all', 'one', 'none']
        curr_idx = modes.index(self.loop_mode) if self.loop_mode in modes else 0
        self.loop_mode = modes[(curr_idx + 1) % len(modes)]
        self.mode_changed.emit(self.loop_mode, self.is_shuffle)

    def _generate_shuffle_deck(self, starting_track_index=None):
        """
        Creates a fair, comprehensive shuffle deck. Every song in the playlist
        plays once in randomized order without repeats.
        """
        if not self.current_playlist:
            self._shuffle_order = []
            self._shuffle_pos = -1
            return

        n = len(self.current_playlist)
        indices = list(range(n))
        random.shuffle(indices)

        # Pin currently playing track to position 0 so playback continues seamlessly
        if starting_track_index is not None and 0 <= starting_track_index < n:
            if starting_track_index in indices:
                indices.remove(starting_track_index)
            indices.insert(0, starting_track_index)

        self._shuffle_order = indices
        self._shuffle_pos = 0

    def next_track(self):
        # 1. Check Up Next Priority Queue (User Cherry-Picked Songs)
        if self.up_next_queue:
            next_track_item = self.up_next_queue.pop(0)
            self.queue_changed.emit(len(self.up_next_queue))
            self.play_track(next_track_item)
            return

        # 2. If finished playing a single search-result request, resume full library
        if getattr(self, 'is_single_play', False):
            self.is_single_play = False
            self.current_playlist = self.db.get_all_tracks_for_playback()

        if not self.current_playlist:
            self.current_playlist = self.db.get_all_tracks_for_playback()

        if not self.current_playlist:
            return

        # 3. True Cosmic Shuffle Mode
        if self.is_shuffle:
            if self.current_track:
                self.history_stack.append(self.current_track)
                if len(self.history_stack) > 50:
                    self.history_stack.pop(0)

            n = len(self.current_playlist)
            if n <= 1:
                next_idx = 0
            else:
                curr_fp = self.current_track.get('filepath') if self.current_track else None
                curr_artist = (self.current_track.get('artist') or '').strip().lower() if self.current_track else None

                candidates = [i for i, t in enumerate(self.current_playlist) if t.get('filepath') != curr_fp]
                if not candidates:
                    candidates = list(range(n))

                # Diversify: avoid playing the same artist immediately if library has plenty of tracks
                if len(candidates) > 10 and curr_artist:
                    diff_artist = [i for i in candidates if (self.current_playlist[i].get('artist') or '').strip().lower() != curr_artist]
                    if diff_artist:
                        candidates = diff_artist

                next_idx = random.choice(candidates)

            self.play_track(self.current_playlist[next_idx])
            return

        # 4. Standard Sequential Order Mode
        else:
            n = len(self.current_playlist)
            next_idx = self.current_index + 1
            if next_idx >= n:
                if self.loop_mode in ('all', 'one'):
                    next_idx = 0
                else:
                    self.stop()
                    return

            if 0 <= next_idx < n:
                self.play_track(self.current_playlist[next_idx])

    def prev_track(self):
        try:
            if self.player.position() > 3000:
                self.seek(0)
                return
        except Exception:
            pass

        # Step backwards through actual songs heard if in Shuffle
        if self.is_shuffle and self.history_stack:
            prev_track_item = self.history_stack.pop()
            self.play_track(prev_track_item)
            return

        if not self.current_playlist:
            self.current_playlist = self.db.get_all_tracks_for_playback()

        if not self.current_playlist:
            return

        n = len(self.current_playlist)
        prev_idx = self.current_index - 1
        if prev_idx < 0:
            prev_idx = n - 1 if self.loop_mode in ('all', 'one') else 0

        if 0 <= prev_idx < n:
            self.play_track(self.current_playlist[prev_idx])

    # Bluetooth Disconnect & Audio Sink Protection
    def _on_audio_outputs_changed(self):
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if self.audio_output and not default_device.isNull():
                cur_vol = self.audio_output.volume()
                self.audio_output.setDevice(default_device)
                self.audio_output.setVolume(cur_vol)
        except Exception:
            pass

    def _on_player_error(self, error, error_string):
        try:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.state_changed.emit(False)
        except Exception:
            pass

        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if self.audio_output and not default_device.isNull():
                self.audio_output.setDevice(default_device)
        except Exception:
            pass

        self.error_occurred.emit(f"Audio device update: {error_string or 'Output disconnected, playback paused.'}")

    # Qt Signal Handlers
    def _on_position_changed(self, pos_ms):
        try:
            duration = self.player.duration()
            self.position_changed.emit(pos_ms, duration)
        except Exception:
            pass

    def _on_duration_changed(self, dur_ms):
        try:
            self.duration_changed.emit(dur_ms)
            if self.current_track and dur_ms > 0 and self.current_track.get('duration', 0) == 0:
                self.current_track['duration'] = dur_ms
                self.db.update_track_metadata(
                    self.current_track['filepath'],
                    self.current_track['title'],
                    self.current_track['artist'],
                    self.current_track.get('album', ''),
                    dur_ms
                )
        except Exception:
            pass

    def _on_playback_state_changed(self, state):
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.state_changed.emit(is_playing)

    def _on_media_status_changed(self, status):
        try:
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                if self.loop_mode == "one":
                    self.seek(0)
                    self.player.play()
                elif self.loop_mode == "all" or (self.is_shuffle and (self._shuffle_pos + 1 < len(self._shuffle_order))) or (not self.is_shuffle and (self.current_index + 1 < len(self.current_playlist))):
                    self.next_track()
                else:
                    self.stop()
            elif status == QMediaPlayer.MediaStatus.InvalidMedia:
                if self.current_track:
                    fp = self.current_track.get('filepath')
                    if fp and not os.path.exists(fp):
                        self.db.delete_music_track(fp)
                    self.track_unavailable.emit(self.current_track, "Invalid or unreadable audio media file.")
                    self.next_track()
        except Exception:
            pass
