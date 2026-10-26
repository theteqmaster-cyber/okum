import os
from PyQt6.QtCore import Qt, QPoint, QRectF, QSize, QByteArray
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QPixmap, QIcon, QCursor, QGuiApplication,
    QLinearGradient
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFrame
)
from PyQt6.QtMultimedia import QMediaPlayer

from services.music_service import MusicService, CoverArtCache

SVG_GRIP = '<circle cx="9" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="15" cy="18" r="1.5"/>'
SVG_PREV = '<polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5"/>'
SVG_PLAY = '<polygon points="5 3 19 12 5 21 5 3"/>'
SVG_PAUSE = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
SVG_NEXT = '<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/>'
SVG_RESTORE = '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>'
SVG_CLOSE = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'

def create_svg_icon(svg_inner, stroke_color='#f3f4f6', fill_color='none', size=16, stroke_width=2):
    svg_xml = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">
    {svg_inner}
    </svg>'''
    renderer = QSvgRenderer(QByteArray(svg_xml.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class FloatingMusicWindow(QWidget):
    """
    Okum Floating Mini Music Player:
    A sleek, draggable, always-on-top pill widget designed for quick song switching
    with zero desktop friction. Does not steal keyboard focus from active workflows.
    """
    _instance = None

    def __init__(self, open_big_window_callback=None):
        super().__init__()
        self.open_big_window_callback = open_big_window_callback
        self.music_service = MusicService.get_instance()

        # Frameless, Always on Top, Non-activating tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setWindowTitle("Okum Mini Player")
        self.setObjectName("FloatingMusicWindow")

        # Stable global drag state
        self._dragging = False
        self._drag_offset = QPoint()
        self._saved_pos = None

        self._init_ui()
        self._bind_music_signals()
        self._refresh_state()

        # Comfortable width with breathing room for song title & controls
        self.setFixedSize(430, 48)

    @classmethod
    def get_instance(cls, open_big_window_callback=None):
        if cls._instance is None:
            cls._instance = FloatingMusicWindow(open_big_window_callback)
        elif open_big_window_callback is not None:
            cls._instance.open_big_window_callback = open_big_window_callback
        return cls._instance

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        # 1. Drag Grip Handle
        self.lbl_grip = QLabel(self)
        self.lbl_grip.setPixmap(create_svg_icon(SVG_GRIP, stroke_color="#6b7280", size=14).pixmap(14, 14))
        self.lbl_grip.setToolTip("Drag mini player anywhere")
        self.lbl_grip.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        layout.addWidget(self.lbl_grip)

        # 2. Album Art Thumbnail (30x30)
        self.lbl_art = QLabel(self)
        self.lbl_art.setFixedSize(30, 30)
        self.lbl_art.setStyleSheet("border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.15);")
        self.lbl_art.setScaledContents(True)
        self.lbl_art.setPixmap(CoverArtCache.get_default_pixmap(30))
        layout.addWidget(self.lbl_art)

        # 3. Compact Song Info (Title + Artist)
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 1, 0, 1)

        self.lbl_title = QLabel("No track playing", self)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        self.lbl_title.setMinimumWidth(120)
        self.lbl_title.setMaximumWidth(160)

        self.lbl_artist = QLabel("Quick Play", self)
        self.lbl_artist.setStyleSheet("font-size: 9.5px; color: #38bdf8;")
        self.lbl_artist.setMinimumWidth(120)
        self.lbl_artist.setMaximumWidth(160)

        text_col.addWidget(self.lbl_title)
        text_col.addWidget(self.lbl_artist)
        layout.addLayout(text_col, 1)

        # Separator 1
        sep1 = QFrame(self)
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: rgba(255, 255, 255, 0.14); margin: 6px 1px;")
        layout.addWidget(sep1)

        # 4. Previous Button
        self.btn_prev = QPushButton(self)
        self.btn_prev.setIcon(create_svg_icon(SVG_PREV, stroke_color="#f3f4f6", size=14))
        self.btn_prev.setIconSize(QSize(14, 14))
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setObjectName("btnMiniPrev")
        self.btn_prev.setToolTip("Previous Track")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.btn_prev)

        # 5. Play / Pause Button
        self.btn_play = QPushButton(self)
        self.btn_play.setIcon(create_svg_icon(SVG_PLAY, stroke_color="#ffffff", fill_color="#ffffff", size=15))
        self.btn_play.setIconSize(QSize(15, 15))
        self.btn_play.setFixedSize(32, 32)
        self.btn_play.setObjectName("btnMiniPlay")
        self.btn_play.setToolTip("Play / Pause")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.btn_play)

        # 6. Next Button
        self.btn_next = QPushButton(self)
        self.btn_next.setIcon(create_svg_icon(SVG_NEXT, stroke_color="#f3f4f6", size=14))
        self.btn_next.setIconSize(QSize(14, 14))
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setObjectName("btnMiniNext")
        self.btn_next.setToolTip("Next Track")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.btn_next)

        # Separator 2
        sep2 = QFrame(self)
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: rgba(255, 255, 255, 0.14); margin: 6px 1px;")
        layout.addWidget(sep2)

        # 7. Restore / Expand to Big Music Window Button
        self.btn_restore = QPushButton(self)
        self.btn_restore.setIcon(create_svg_icon(SVG_RESTORE, stroke_color="#38bdf8", size=14))
        self.btn_restore.setIconSize(QSize(14, 14))
        self.btn_restore.setFixedSize(28, 28)
        self.btn_restore.setObjectName("btnMiniRestore")
        self.btn_restore.setToolTip("Switch to Full Music Window")
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.clicked.connect(self._on_restore_clicked)
        layout.addWidget(self.btn_restore)

        # 8. Close Button
        self.btn_close = QPushButton(self)
        self.btn_close.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#94a3b8", size=14))
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setObjectName("btnMiniClose")
        self.btn_close.setToolTip("Close Mini Player")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._on_close_clicked)
        layout.addWidget(self.btn_close)

        # Apply robust control styles
        self._apply_control_styles()

    def _apply_control_styles(self):
        self.setStyleSheet("""
            QPushButton#btnMiniPrev, QPushButton#btnMiniNext {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton#btnMiniPrev:hover, QPushButton#btnMiniNext:hover {
                background-color: rgba(99, 102, 241, 0.38);
                border-color: #818cf8;
            }
            QPushButton#btnMiniPlay {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                border: 1px solid rgba(165, 180, 252, 0.6);
                border-radius: 16px;
                padding: 0px;
            }
            QPushButton#btnMiniPlay:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #818cf8, stop:1 #6366f1);
                border-color: #e0e7ff;
            }
            QPushButton#btnMiniRestore {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton#btnMiniRestore:hover {
                background-color: rgba(6, 182, 212, 0.32);
                border-color: #06b6d4;
            }
            QPushButton#btnMiniClose {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton#btnMiniClose:hover {
                background-color: rgba(239, 68, 68, 0.32);
                border-color: #ef4444;
            }
        """)

    def _bind_music_signals(self):
        if self.music_service:
            self.music_service.track_changed.connect(self._on_track_changed)
            self.music_service.state_changed.connect(self._on_state_changed)
            if hasattr(self.music_service, 'player'):
                self.music_service.player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _on_playback_state_changed(self, state):
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self._on_state_changed(is_playing)

    def _refresh_state(self):
        if not self.music_service:
            return
        self._on_track_changed(self.music_service.current_track)
        is_playing = (self.music_service.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        self._on_state_changed(is_playing)

    def _on_track_changed(self, track):
        if not track:
            self.lbl_title.setText("No track playing")
            self.lbl_artist.setText("Quick Play • Ready")
            self.lbl_art.setPixmap(CoverArtCache.get_default_pixmap(30))
            self.setToolTip("Okum Floating Mini Music Player")
            return

        title = track.get('title') or track.get('filename') or "Unknown Track"
        artist = track.get('artist') or "Local Music"
        fp = track.get('filepath', '')
        play_count = track.get('play_count', 0) or 0

        # Clean elision with ellipsis up to 155px
        metrics = self.lbl_title.fontMetrics()
        elided_title = metrics.elidedText(title, Qt.TextElideMode.ElideRight, 155)
        self.lbl_title.setText(elided_title)

        artist_metrics = self.lbl_artist.fontMetrics()
        elided_artist = artist_metrics.elidedText(artist, Qt.TextElideMode.ElideRight, 155)
        self.lbl_artist.setText(elided_artist)

        self.lbl_art.setPixmap(CoverArtCache.get_cover_pixmap(fp, size=30))

        plays_str = f" • {play_count} plays" if play_count > 0 else ""
        full_tip = f"{title}\n{artist}{plays_str}\n(Click & drag anywhere to move)"
        self.setToolTip(full_tip)
        self.lbl_title.setToolTip(full_tip)

    def _on_state_changed(self, is_playing):
        if is_playing:
            self.btn_play.setIcon(create_svg_icon(SVG_PAUSE, stroke_color="#ffffff", fill_color="#ffffff", size=15))
            self.btn_play.setToolTip("Pause Playback")
        else:
            self.btn_play.setIcon(create_svg_icon(SVG_PLAY, stroke_color="#ffffff", fill_color="#ffffff", size=15))
            self.btn_play.setToolTip("Resume Playback")

    def _on_prev_clicked(self):
        if self.music_service:
            self.music_service.prev_track()

    def _on_next_clicked(self):
        if self.music_service:
            self.music_service.next_track()

    def _on_play_clicked(self):
        if self.music_service:
            self.music_service.toggle_play_pause()
            # Optimistic instant icon toggle for snappy responsiveness
            is_now_playing = (self.music_service.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
            self._on_state_changed(not is_now_playing)

    def _on_restore_clicked(self):
        self.hide()
        if self.open_big_window_callback:
            self.open_big_window_callback()

    def _on_close_clicked(self):
        self.hide()

    # Dragging logic: Global coordinates prevents jitter and rubber-banding
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            target_pos = event.globalPosition().toPoint() - self._drag_offset
            screen = QGuiApplication.primaryScreen().availableGeometry()
            px = max(8, min(screen.x() + screen.width() - self.width() - 8, target_pos.x()))
            py = max(8, min(screen.y() + screen.height() - self.height() - 8, target_pos.y()))
            self.move(px, py)
            self._saved_pos = self.pos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._saved_pos = self.pos()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        # Deep obsidian indigo gradient
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0, QColor(24, 28, 48, 250))
        grad.setColorAt(1.0, QColor(14, 17, 30, 252))

        border_pen = QPen(QColor(99, 102, 241, 175), 1.5)
        painter.setPen(border_pen)
        painter.setBrush(grad)
        painter.drawRoundedRect(rect, 14.0, 14.0)

        # Subtle top gleam
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
        painter.drawLine(int(rect.x() + 14), int(rect.y() + 1), int(rect.right() - 14), int(rect.y() + 1))

    def _position_initial(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.x() + screen.width() - self.width() - 24
        y = screen.y() + screen.height() - self.height() - 24
        self.move(x, y)
        self._saved_pos = self.pos()

    def show_player(self):
        if self._saved_pos is None:
            self._position_initial()
        else:
            self.move(self._saved_pos)
        self._refresh_state()
        self.show()
        self.raise_()

    def hide_player(self):
        self.hide()

    def toggle_player(self):
        if self.isVisible():
            self.hide_player()
        else:
            self.show_player()
