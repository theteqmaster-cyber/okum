import os
import random
import hashlib
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QThread
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

def get_music_dir():
    candidates = [
        os.path.expanduser('~/Music'),
        os.path.expanduser('~/music')
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.expanduser('~/Music')

class MetadataScanWorker(QThread):
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

        total = len(self.tracks)
        for i, track in enumerate(self.tracks):
            if self._is_cancelled:
                break
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

            if i % 25 == 0 or i == total - 1:
                self.progress.emit(i + 1, total)

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

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.music_dir = get_music_dir()

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

        # Scanner worker
        self._scan_worker = None

        # Perform quick initial library scan & prune deleted files
        self.scan_library_fast()

    @classmethod
    def get_instance(cls, db=None):
        if cls._instance is None and db is not None:
            cls._instance = MusicService(db)
        return cls._instance

    def scan_library_fast(self):
        """Scans the music directory in milliseconds, indexes new songs, and removes deleted files."""
        # 1. Safety Check: Prune missing / deleted tracks from database
        all_db_tracks = self.db.get_all_music_filepaths()
        missing_filepaths = []
        for row in all_db_tracks:
            fp = row.get('filepath')
            if fp and not os.path.exists(fp):
                missing_filepaths.append(fp)
        
        if missing_filepaths:
            self.db.delete_music_tracks_batch(missing_filepaths)

        if not os.path.exists(self.music_dir):
            total_count = self.db.get_music_tracks_count()
            self.library_scanned.emit(total_count)
            return

        tracks_to_insert = []
        tracks_need_metadata = []

        existing_db_tracks = {row['filepath']: row for row in self.db.get_all_music_filepaths()}

        for root, _, files in os.walk(self.music_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in VALID_AUDIO_EXTS:
                    full_p = os.path.join(root, f)
                    if full_p not in existing_db_tracks:
                        name_no_ext = os.path.splitext(f)[0]
                        if ' - ' in name_no_ext:
                            parts = name_no_ext.split(' - ', 1)
                            artist, title = parts[0].strip(), parts[1].strip()
                        else:
                            artist, title = 'Local Music', name_no_ext

                        track_id = hashlib.md5(full_p.encode('utf-8')).hexdigest()[:16]
                        track_item = {
                            'id': track_id,
                            'filepath': full_p,
                            'filename': f,
                            'title': title,
                            'artist': artist,
                            'album': '',
                            'duration': 0,
                            'ext': ext
                        }
                        tracks_to_insert.append(track_item)
                        tracks_need_metadata.append(track_item)
                    elif existing_db_tracks[full_p]['duration'] == 0:
                        tracks_need_metadata.append({'filepath': full_p, 'title': '', 'artist': ''})

        if tracks_to_insert:
            self.db.upsert_music_tracks_batch(tracks_to_insert)

        total_count = self.db.get_music_tracks_count()
        self.library_scanned.emit(total_count)

        # Launch background metadata scan for missing tags if any
        if tracks_need_metadata:
            self._start_background_metadata_scan(tracks_need_metadata)

    def _start_background_metadata_scan(self, tracks):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait()

        self._scan_worker = MetadataScanWorker(self.db, tracks)
        self._scan_worker.start()

    # Playback Controls with Safety Checks
    def play_track(self, track_dict, playlist=None, _attempt_count=0):
        if playlist is not None:
            self.current_playlist = list(playlist)

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
            # Prune from DB
            if filepath:
                self.db.delete_music_track(filepath)
            
            # Remove from active playlist
            self.current_playlist = [t for t in self.current_playlist if t.get('filepath') != filepath]
            
            song_name = track_dict.get('title') or track_dict.get('filename') or 'Song'
            self.track_unavailable.emit(track_dict, f"File not found: '{song_name}' (removed from library).")
            
            # Try to advance safely to next track
            if self.current_playlist:
                next_idx = self.current_index if self.current_index < len(self.current_playlist) else 0
                next_track_item = self.current_playlist[next_idx]
                self.play_track(next_track_item, self.current_playlist, _attempt_count=_attempt_count + 1)
            else:
                self.stop()
            return

        try:
            self.current_index = next(i for i, t in enumerate(self.current_playlist) if t['filepath'] == filepath)
        except StopIteration:
            self.current_playlist.append(track_dict)
            self.current_index = len(self.current_playlist) - 1

        self._update_shuffle_indices()

        self.current_track = track_dict
        
        try:
            self.player.setSource(QUrl.fromLocalFile(filepath))
            self.player.play()
            self.track_changed.emit(self.current_track)
            self.state_changed.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"Player error loading track: {str(e)}")

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

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        self._update_shuffle_indices()
        self.mode_changed.emit(self.loop_mode, self.is_shuffle)

    def cycle_loop_mode(self):
        modes = ['all', 'one', 'none']
        curr_idx = modes.index(self.loop_mode) if self.loop_mode in modes else 0
        self.loop_mode = modes[(curr_idx + 1) % len(modes)]
        self.mode_changed.emit(self.loop_mode, self.is_shuffle)

    def _update_shuffle_indices(self):
        if not self.current_playlist:
            self._shuffle_order = []
            self._shuffle_pos = -1
            return

        n = len(self.current_playlist)
        self._shuffle_order = list(range(n))
        if self.is_shuffle:
            random.shuffle(self._shuffle_order)
            if 0 <= self.current_index < n and self.current_index in self._shuffle_order:
                self._shuffle_order.remove(self.current_index)
                self._shuffle_order.insert(0, self.current_index)
                self._shuffle_pos = 0
            else:
                self._shuffle_pos = 0
        else:
            self._shuffle_pos = self.current_index

    def next_track(self):
        if not self.current_playlist:
            return

        n = len(self.current_playlist)
        if self.is_shuffle:
            if not self._shuffle_order or len(self._shuffle_order) != n:
                self._update_shuffle_indices()
            self._shuffle_pos += 1
            if self._shuffle_pos >= n:
                if self.loop_mode in ('all', 'one'):
                    self._update_shuffle_indices()
                    self._shuffle_pos = 0
                else:
                    self.stop()
                    return
            next_idx = self._shuffle_order[self._shuffle_pos]
        else:
            next_idx = self.current_index + 1
            if next_idx >= n:
                if self.loop_mode in ('all', 'one'):
                    next_idx = 0
                else:
                    self.stop()
                    return

        if 0 <= next_idx < len(self.current_playlist):
            self.play_track(self.current_playlist[next_idx], self.current_playlist)

    def prev_track(self):
        if not self.current_playlist:
            return

        # If played more than 3 seconds, restart current track
        try:
            if self.player.position() > 3000:
                self.seek(0)
                return
        except Exception:
            pass

        n = len(self.current_playlist)
        if self.is_shuffle:
            if not self._shuffle_order:
                self._update_shuffle_indices()
            self._shuffle_pos -= 1
            if self._shuffle_pos < 0:
                self._shuffle_pos = n - 1
            prev_idx = self._shuffle_order[self._shuffle_pos]
        else:
            prev_idx = self.current_index - 1
            if prev_idx < 0:
                prev_idx = n - 1

        if 0 <= prev_idx < len(self.current_playlist):
            self.play_track(self.current_playlist[prev_idx], self.current_playlist)

    # Bluetooth Disconnect & Audio Sink Protection
    def _on_audio_outputs_changed(self):
        """Safely re-binds audio device when Bluetooth/USB audio device disconnects or reconnects."""
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if self.audio_output and not default_device.isNull():
                cur_vol = self.audio_output.volume()
                self.audio_output.setDevice(default_device)
                self.audio_output.setVolume(cur_vol)
        except Exception:
            pass

    def _on_player_error(self, error, error_string):
        """Intercepts QMediaPlayer errors (e.g. bluetooth disconnect) to prevent process crash."""
        try:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.state_changed.emit(False)
        except Exception:
            pass

        # Recover audio output device if lost
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
                elif self.loop_mode == "all" or (self.current_index + 1 < len(self.current_playlist)):
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
