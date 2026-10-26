from PyQt6.QtCore import Qt, QPoint, QRectF, QSize, QByteArray, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QTextDocument, QPixmap, QIcon, QFont,
    QPainterPath, QLinearGradient, QBrush
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QButtonGroup, QFrame, QStackedWidget,
    QScrollArea, QListWidget, QListWidgetItem, QSlider, QComboBox
)

import math
import os
import html
import markdown

from services.ai_service import AIQueryWorker
from services.music_service import MusicService, format_time_ms, CoverArtCache
from ui.board_window import OkumBoardManager

# Drawn SVG Vector Icons
SVG_NOTE = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'
SVG_SPARKLES = '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3z"/>'
SVG_MUSIC = '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'
SVG_BOARD = '<path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/><path d="M14 6l4 4"/><path d="M4 20h16"/>'
SVG_PIN = '<line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-1.5-6V5.5A1.5 1.5 0 0 0 16 4H8a1.5 1.5 0 0 0-1.5 1.5V11L5 17z"/>'
SVG_PLUS = '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
SVG_CHECK = '<polyline points="20 6 9 17 4 12"/>'
SVG_EXPAND = '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>'
SVG_CLOSE = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
SVG_SEND = '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>'

SVG_PLAY = '<polygon points="6 4 20 12 6 20 6 4"/>'
SVG_PAUSE = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
SVG_PREV = '<polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5"/>'
SVG_NEXT = '<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/>'
SVG_SHUFFLE = '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>'
SVG_REPEAT = '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'
SVG_REPEAT_ONE = '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/><text x="10" y="15" font-size="7" font-weight="bold" fill="#ffffff" stroke="none">1</text>'
SVG_REFRESH = '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
SVG_SEARCH = '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
SVG_MINI_PLAYER = '<rect x="2" y="4" width="20" height="16" rx="2"/><rect x="12" y="10" width="7" height="6" rx="1"/>'

def create_svg_icon(svg_inner, stroke_color='#f3f4f6', fill_color='none', size=18, stroke_width=2):
    svg_xml = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">
    {svg_inner}
    </svg>'''
    renderer = QSvgRenderer(QByteArray(svg_xml.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def format_chat_text(text):
    if not text:
        return ""
    try:
        html = markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])
        html = html.replace('<code>', '<code style="background: rgba(255, 255, 255, 0.12); color: #a5b4fc; padding: 1px 5px; border-radius: 4px; font-family: monospace;">')
        html = html.replace('<pre>', '<pre style="background: rgba(10, 12, 22, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); padding: 8px; border-radius: 6px; white-space: pre-wrap; word-wrap: break-word;">')
        html = html.replace('<p>', '<p style="margin: 0 0 6px 0; line-height: 1.45;">')
        html = html.replace('<ul>', '<ul style="margin: 4px 0 6px 14px; padding-left: 10px;">')
        html = html.replace('<ol>', '<ol style="margin: 4px 0 6px 14px; padding-left: 10px;">')
        html = html.replace('<li>', '<li style="margin-bottom: 2px; line-height: 1.4;">')
        return html
    except Exception:
        escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        return f"<p style='margin:0;'>{escaped}</p>"

class NowPlayingHeroCard(QFrame):
    """
    Sleek, hardware-accelerated hero card displaying an ultra-fast, low-blur
    semi-transparent cover art wallpaper with dark glassmorphic vignette.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nowPlayingCard")
        self._bg_wallpaper = None

    def set_wallpaper_pixmap(self, pixmap):
        self._bg_wallpaper = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        card_w, card_h = rect.width(), rect.height()

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, card_w - 1, card_h - 1), 12.0, 12.0)
        painter.setClipPath(path)

        # 1. Base dark obsidian/indigo backdrop
        painter.fillRect(QRectF(0, 0, card_w, card_h), QColor(14, 17, 28, 255))

        # 2. Subtle low-blur, transparent cover art wallpaper
        if self._bg_wallpaper and not self._bg_wallpaper.isNull():
            painter.setOpacity(0.24)
            dx = (card_w - self._bg_wallpaper.width()) // 2
            dy = (card_h - self._bg_wallpaper.height()) // 2
            painter.drawPixmap(dx, dy, self._bg_wallpaper)

        # 3. Delicate vignette overlay for 100% text/control legibility
        painter.setOpacity(1.0)
        grad = QLinearGradient(0, 0, 0, card_h)
        grad.setColorAt(0.0, QColor(14, 17, 28, 65))
        grad.setColorAt(0.55, QColor(14, 17, 28, 120))
        grad.setColorAt(1.0, QColor(10, 12, 22, 215))
        painter.fillRect(QRectF(0, 0, card_w, card_h), grad)

        # 4. Refined subtle border
        painter.setPen(QPen(QColor(99, 102, 241, 95), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, card_w - 1, card_h - 1), 12.0, 12.0)

class QuickWindow(QWidget):
    PAGE_SIZE = 50

    def __init__(self, db, open_dashboard_callback):
        super().__init__()
        self.db = db
        self.open_dashboard_callback = open_dashboard_callback
        self.music_service = MusicService.get_instance(self.db)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(400, 510)
        self.setObjectName("QuickWindow")

        # Note state
        self.current_note_id = None
        self.current_category = "General"
        self.is_pinned = False
        self._saved_snapshot = {'title': '', 'content': '', 'category': 'General', 'pinned': False}

        # Chat state
        self.active_session = None
        self.current_worker = None

        # Music state
        self.music_page = 1
        self.total_music_pages = 1
        self.total_music_count = 0
        self.current_displayed_tracks = []
        self._user_seeking = False

        # Dragging state
        self._dragging = False
        self._drag_position = QPoint()

        # Note auto-save timer (debounced 600ms while typing)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(600)
        self.autosave_timer.timeout.connect(self._perform_autosave)

        self._init_ui()
        self._init_ai_provider()
        self._load_active_chat_session()
        self._bind_music_signals()
        self._load_music_library()

    def hideEvent(self, event):
        self._flush_autosave()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._flush_autosave()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())

        # Glass Card Backdrop
        bg_color = QColor(18, 22, 38, 245)
        border_pen = QPen(QColor(99, 102, 241, 140), 1.5)

        painter.setPen(border_pen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 16.0, 16.0)

    def _init_ui(self):
        # Container
        self.container = QFrame(self)
        self.container.setObjectName("QuickWindowContainer")
        self.container.setGeometry(0, 0, 400, 510)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # 1. Top Bar / Header with Okum Assistant title and icon tab buttons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        self.lbl_title = QLabel("Okum Assistant", self)
        self.lbl_title.setObjectName("titleLabel")
        self.lbl_sub = QLabel("● Brain: qwen2.5:1.5b", self)
        self.lbl_sub.setObjectName("subLabel")
        self.lbl_sub.setStyleSheet("color: #10b981; font-weight: 500; font-size: 10px;")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Icon-only tab buttons
        self.btn_tab_notes = QPushButton(self)
        self.btn_tab_notes.setIcon(create_svg_icon(SVG_NOTE, stroke_color="#f3f4f6", size=18))
        self.btn_tab_notes.setIconSize(QSize(18, 18))
        self.btn_tab_notes.setFixedSize(32, 32)
        self.btn_tab_notes.setToolTip("Quick Note")
        self.btn_tab_notes.setCheckable(True)
        self.btn_tab_notes.setChecked(True)
        self.btn_tab_notes.setObjectName("btnTabIcon")

        self.btn_tab_ask = QPushButton(self)
        self.btn_tab_ask.setIcon(create_svg_icon(SVG_SPARKLES, stroke_color="#f3f4f6", size=18))
        self.btn_tab_ask.setIconSize(QSize(18, 18))
        self.btn_tab_ask.setFixedSize(32, 32)
        self.btn_tab_ask.setToolTip("Ask Okum AI")
        self.btn_tab_ask.setCheckable(True)
        self.btn_tab_ask.setObjectName("btnTabIcon")

        self.btn_tab_music = QPushButton(self)
        self.btn_tab_music.setIcon(create_svg_icon(SVG_MUSIC, stroke_color="#f3f4f6", size=18))
        self.btn_tab_music.setIconSize(QSize(18, 18))
        self.btn_tab_music.setFixedSize(32, 32)
        self.btn_tab_music.setToolTip("Quick Play (Music Player)")
        self.btn_tab_music.setCheckable(True)
        self.btn_tab_music.setObjectName("btnTabIcon")

        self.btn_tab_board = QPushButton(self)
        self.btn_tab_board.setIcon(create_svg_icon(SVG_BOARD, stroke_color="#f3f4f6", size=18))
        self.btn_tab_board.setIconSize(QSize(18, 18))
        self.btn_tab_board.setFixedSize(32, 32)
        self.btn_tab_board.setToolTip("Okum Board (Screen Annotations)")
        self.btn_tab_board.setObjectName("btnTabIcon")
        self.btn_tab_board.clicked.connect(self._toggle_board)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.btn_tab_notes, 0)
        self.tab_group.addButton(self.btn_tab_ask, 1)
        self.tab_group.addButton(self.btn_tab_music, 2)

        self.btn_tab_notes.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_ask.clicked.connect(lambda: self._switch_tab(1))
        self.btn_tab_music.clicked.connect(lambda: self._switch_tab(2))

        header_layout.addWidget(self.btn_tab_notes)
        header_layout.addWidget(self.btn_tab_ask)
        header_layout.addWidget(self.btn_tab_music)
        header_layout.addWidget(self.btn_tab_board)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.15); margin: 4px 2px;")
        header_layout.addWidget(sep)

        self.btn_dash = QPushButton(self)
        self.btn_dash.setIcon(create_svg_icon(SVG_EXPAND, stroke_color="#94a3b8", size=16))
        self.btn_dash.setIconSize(QSize(16, 16))
        self.btn_dash.setToolTip("Open Dashboard")
        self.btn_dash.setFixedSize(28, 28)
        self.btn_dash.setObjectName("btnHeaderControl")
        self.btn_dash.clicked.connect(self._on_expand_dashboard)

        self.btn_close = QPushButton(self)
        self.btn_close.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#94a3b8", size=16))
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.setToolTip("Close (Esc)")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setObjectName("btnHeaderControl")
        self.btn_close.clicked.connect(self.hide)

        header_layout.addWidget(self.btn_dash)
        header_layout.addWidget(self.btn_close)

        main_layout.addLayout(header_layout)

        # 2. Stacked View (Tab 0: Notes, Tab 1: Ask Okum, Tab 2: Quick Play)
        self.view_stack = QStackedWidget(self)

        # --- VIEW 0: QUICK NOTE ---
        self.page_note = QWidget()
        note_layout = QVBoxLayout(self.page_note)
        note_layout.setContentsMargins(0, 4, 0, 0)
        note_layout.setSpacing(8)

        self.txt_title = QLineEdit(self)
        self.txt_title.setObjectName("noteTitle")
        self.txt_title.setPlaceholderText("Title or quick thought...")
        self.txt_title.textChanged.connect(self._on_note_content_changed)
        note_layout.addWidget(self.txt_title)

        cat_layout = QHBoxLayout()
        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)

        categories = ["General", "Ideas", "Tasks", "Recent"]
        for cat in categories:
            btn = QPushButton(cat, self)
            btn.setObjectName("btnCategory")
            btn.setCheckable(True)
            if cat == "General":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=cat: self._on_category_button_clicked(c))
            self.cat_group.addButton(btn)
            cat_layout.addWidget(btn)

        cat_layout.addStretch()

        self.btn_pin = QPushButton(self)
        self.btn_pin.setIcon(create_svg_icon(SVG_PIN, stroke_color="#d1d5db", size=16))
        self.btn_pin.setIconSize(QSize(16, 16))
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setObjectName("btnCategoryIcon")
        self.btn_pin.setToolTip("Pin Note to Top")
        self.btn_pin.setCheckable(True)
        self.btn_pin.clicked.connect(self._toggle_pin)
        cat_layout.addWidget(self.btn_pin)

        note_layout.addLayout(cat_layout)

        # Note Body Stack (0: Editor View, 1: Recent Notes List View)
        self.note_body_stack = QStackedWidget(self.page_note)

        # Body Stack 0: Text Content Editor
        self.txt_content = QTextEdit(self.page_note)
        self.txt_content.setObjectName("noteContent")
        self.txt_content.setPlaceholderText("Type your note here...")
        self.txt_content.textChanged.connect(self._on_note_content_changed)
        self.note_body_stack.addWidget(self.txt_content)

        # Body Stack 1: Recent Notes View (Search + List)
        self.page_recent = QWidget(self.page_note)
        recent_layout = QVBoxLayout(self.page_recent)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(6)

        recent_search_box = QHBoxLayout()
        recent_search_box.setSpacing(6)

        self.txt_recent_search = QLineEdit(self.page_recent)
        self.txt_recent_search.setPlaceholderText("Search notes by title or content...")
        self.txt_recent_search.textChanged.connect(self._load_recent_notes)
        recent_search_box.addWidget(self.txt_recent_search)

        self.btn_clear_recent = QPushButton(self.page_recent)
        self.btn_clear_recent.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#9ca3af", size=14))
        self.btn_clear_recent.setObjectName("btnPlayerControl")
        self.btn_clear_recent.setFixedSize(28, 28)
        self.btn_clear_recent.setToolTip("Clear Search")
        self.btn_clear_recent.clicked.connect(self.txt_recent_search.clear)
        recent_search_box.addWidget(self.btn_clear_recent)

        recent_layout.addLayout(recent_search_box)

        self.lst_recent_notes = QListWidget(self.page_recent)
        self.lst_recent_notes.setObjectName("lstRecentNotes")
        self.lst_recent_notes.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lst_recent_notes.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lst_recent_notes.itemClicked.connect(self._on_recent_note_selected)
        self.lst_recent_notes.itemDoubleClicked.connect(self._on_recent_note_selected)
        recent_layout.addWidget(self.lst_recent_notes)

        self.note_body_stack.addWidget(self.page_recent)

        note_layout.addWidget(self.note_body_stack)

        footer_note = QHBoxLayout()
        footer_note.setSpacing(6)
        footer_note.setContentsMargins(2, 0, 0, 0)
        footer_note.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_save_dot = QLabel("●", self)
        self.lbl_save_dot.setFixedSize(14, 14)
        self.lbl_save_dot.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: bold;")
        self.lbl_save_dot.setToolTip("Empty Note (0 words)")

        self.lbl_words = QLabel("0 words • 0 chars", self)
        self.lbl_words.setObjectName("subLabel")
        self.lbl_words.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.lbl_words.setMinimumWidth(180)
        footer_note.addWidget(self.lbl_save_dot)
        footer_note.addWidget(self.lbl_words)
        footer_note.addStretch()

        self.btn_new = QPushButton(self)
        self.btn_new.setIcon(create_svg_icon(SVG_PLUS, stroke_color="#f3f4f6", size=18))
        self.btn_new.setIconSize(QSize(18, 18))
        self.btn_new.setFixedSize(32, 32)
        self.btn_new.setToolTip("New Note")
        self.btn_new.setObjectName("btnIconSecondary")
        self.btn_new.clicked.connect(self.new_note)

        self.btn_save = QPushButton(self)
        self.btn_save.setIcon(create_svg_icon(SVG_CHECK, stroke_color="#ffffff", size=18))
        self.btn_save.setIconSize(QSize(18, 18))
        self.btn_save.setFixedSize(32, 32)
        self.btn_save.setToolTip("Save Note")
        self.btn_save.setObjectName("btnPrimaryIcon")
        self.btn_save.clicked.connect(self.save_note)

        footer_note.addWidget(self.btn_new)
        footer_note.addWidget(self.btn_save)
        note_layout.addLayout(footer_note)

        self.view_stack.addWidget(self.page_note)

        # --- VIEW 1: ASK OKUM ---
        self.page_ask = QWidget()
        ask_layout = QVBoxLayout(self.page_ask)
        ask_layout.setContentsMargins(0, 4, 0, 0)
        ask_layout.setSpacing(6)

        # AI Engine Switcher Row
        engine_row = QHBoxLayout()
        engine_row.setSpacing(6)
        engine_row.setContentsMargins(2, 0, 2, 2)

        lbl_engine_tag = QLabel("Engine:", self.page_ask)
        lbl_engine_tag.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        engine_row.addWidget(lbl_engine_tag)

        self.combo_ai_provider = QComboBox(self.page_ask)
        self.combo_ai_provider.addItem("⚡ Groq Cloud AI (llama-3.3-70b-versatile)", "groq")
        self.combo_ai_provider.addItem("⚡ Groq Cloud AI (groq/compound)", "groq_compound")
        self.combo_ai_provider.setStyleSheet("""
            QComboBox {
                background-color: rgba(22, 27, 46, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 3px 8px;
                color: #f3f4f6;
                font-size: 11px;
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #6366f1;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox QAbstractItemView {
                background: #111827;
                border: 1px solid rgba(99, 102, 241, 0.5);
                selection-background-color: #4f46e5;
                color: #ffffff;
                padding: 4px;
            }
        """)
        self.combo_ai_provider.currentIndexChanged.connect(self._on_ai_provider_changed)
        engine_row.addWidget(self.combo_ai_provider, 1)

        self.btn_clear_chat_tab = QPushButton(self.page_ask)
        self.btn_clear_chat_tab.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#9ca3af", size=13))
        self.btn_clear_chat_tab.setObjectName("btnPlayerControl")
        self.btn_clear_chat_tab.setFixedSize(24, 24)
        self.btn_clear_chat_tab.setToolTip("Clear current conversation")
        self.btn_clear_chat_tab.clicked.connect(self._clear_current_chat)
        engine_row.addWidget(self.btn_clear_chat_tab)

        ask_layout.addLayout(engine_row)

        # Chat List Box (clean vertical scroll, perfectly calculated item heights)
        self.lst_chat = QListWidget(self)
        self.lst_chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lst_chat.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lst_chat.setSpacing(4)
        self.lst_chat.setStyleSheet("""
            QListWidget { background: transparent; border: none; padding: 2px; }
            QListWidget::item { background: transparent; border: none; margin-bottom: 6px; }
        """)
        ask_layout.addWidget(self.lst_chat)

        # Status / Thinking Indicator
        self.lbl_thinking = QLabel("", self)
        self.lbl_thinking.setStyleSheet("font-size: 11px; color: #8b5cf6; font-style: italic;")
        self.lbl_thinking.hide()
        ask_layout.addWidget(self.lbl_thinking)

        # Input Row
        input_layout = QHBoxLayout()
        self.txt_prompt = QLineEdit(self)
        self.txt_prompt.setPlaceholderText("Ask Okum a quick question...")
        self.txt_prompt.returnPressed.connect(self._send_question)
        input_layout.addWidget(self.txt_prompt)

        self.btn_send = QPushButton(self)
        self.btn_send.setIcon(create_svg_icon(SVG_SEND, stroke_color="#ffffff", size=18))
        self.btn_send.setIconSize(QSize(18, 18))
        self.btn_send.setObjectName("btnPrimaryIcon")
        self.btn_send.setFixedSize(36, 36)
        self.btn_send.setToolTip("Send Question")
        self.btn_send.clicked.connect(self._send_question)
        input_layout.addWidget(self.btn_send)

        ask_layout.addLayout(input_layout)

        self.view_stack.addWidget(self.page_ask)

        # --- VIEW 2: QUICK PLAY (MINI MUSIC PLAYER) ---
        self.page_music = QWidget()
        music_layout = QVBoxLayout(self.page_music)
        music_layout.setContentsMargins(0, 2, 0, 0)
        music_layout.setSpacing(8)

        # 1. Now Playing Glassmorphic Mini Card with Dynamic Blurred Cover Art Wallpaper
        self.card_playing = NowPlayingHeroCard(self.page_music)
        self.card_playing.setStyleSheet("""
            QFrame#nowPlayingCard {
                background: transparent;
                border: none;
            }
        """)
        self.card_playing.set_wallpaper_pixmap(CoverArtCache.get_hero_wallpaper(None))
        card_layout = QVBoxLayout(self.card_playing)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)

        # Top Track Header (Cover Art + Text + Fav/Status)
        track_info_layout = QHBoxLayout()
        track_info_layout.setSpacing(10)

        # Rounded Cover Art Thumbnail (50x50)
        self.lbl_cover_art = QLabel(self.card_playing)
        self.lbl_cover_art.setFixedSize(50, 50)
        self.lbl_cover_art.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.15);")
        self.lbl_cover_art.setScaledContents(True)
        self.lbl_cover_art.setPixmap(CoverArtCache.get_default_pixmap(50))
        track_info_layout.addWidget(self.lbl_cover_art)

        track_text_col = QVBoxLayout()
        track_text_col.setSpacing(2)
        self.lbl_music_track = QLabel("No track playing", self.card_playing)
        self.lbl_music_track.setStyleSheet("background: transparent; font-size: 13px; font-weight: bold; color: #ffffff;")
        self.lbl_music_artist = QLabel("Quick Play • Ready", self.card_playing)
        self.lbl_music_artist.setStyleSheet("background: transparent; font-size: 11px; color: #38bdf8;")

        track_text_col.addWidget(self.lbl_music_track)
        track_text_col.addWidget(self.lbl_music_artist)
        track_info_layout.addLayout(track_text_col, 1)

        # Right badges & actions
        right_status_col = QVBoxLayout()
        right_status_col.setSpacing(3)
        right_status_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        top_actions_row = QHBoxLayout()
        top_actions_row.setSpacing(4)
        top_actions_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Up Next Priority Queue Badge with Clear Action
        self.btn_queue_badge = QPushButton("Up Next: 0 ✕", self.card_playing)
        self.btn_queue_badge.setStyleSheet("""
            QPushButton {
                font-size: 9px; font-weight: bold;
                background: rgba(245, 158, 11, 0.22); color: #fbbf24;
                border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 6px;
                padding: 1px 5px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.3); color: #fca5a5;
                border-color: rgba(239, 68, 68, 0.6);
            }
        """)
        self.btn_queue_badge.setToolTip("Click to clear Up Next queue")
        self.btn_queue_badge.clicked.connect(self.music_service.clear_up_next)
        self.btn_queue_badge.hide()
        top_actions_row.addWidget(self.btn_queue_badge)

        # Favorite Heart Toggle on Card
        self.btn_now_playing_fav = QPushButton("♡", self.card_playing)
        self.btn_now_playing_fav.setFixedSize(22, 22)
        self.btn_now_playing_fav.setStyleSheet("background: transparent; border: none; font-size: 14px; color: #9ca3af;")
        self.btn_now_playing_fav.setToolTip("Toggle Favorite")
        self.btn_now_playing_fav.clicked.connect(self._on_toggle_current_favorite)
        top_actions_row.addWidget(self.btn_now_playing_fav)

        # Floating Mini Player Toggle Button (PiP Mode)
        self.btn_mini_player = QPushButton(self.card_playing)
        self.btn_mini_player.setIcon(create_svg_icon(SVG_MINI_PLAYER, stroke_color="#9ca3af", size=13))
        self.btn_mini_player.setIconSize(QSize(13, 13))
        self.btn_mini_player.setFixedSize(22, 22)
        self.btn_mini_player.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(99, 102, 241, 0.25);
            }
        """)
        self.btn_mini_player.setToolTip("Floating Mini Player (Switch to compact floating widget)")
        self.btn_mini_player.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mini_player.clicked.connect(self._open_floating_mini_player)
        top_actions_row.addWidget(self.btn_mini_player)

        right_status_col.addLayout(top_actions_row)

        self.lbl_music_status_pill = QLabel("Ready", self.card_playing)
        self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(99, 102, 241, 0.25); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; padding: 2px 6px;")
        right_status_col.addWidget(self.lbl_music_status_pill)

        track_info_layout.addLayout(right_status_col)
        card_layout.addLayout(track_info_layout)

        # Progress Scrub Bar
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)

        self.lbl_time_cur = QLabel("00:00", self.card_playing)
        self.lbl_time_cur.setStyleSheet("background: transparent; font-size: 10px; color: #9ca3af; font-family: monospace;")

        self.slider_progress = QSlider(Qt.Orientation.Horizontal, self.card_playing)
        self.slider_progress.setRange(0, 1000)
        self.slider_progress.setValue(0)
        self.slider_progress.sliderPressed.connect(self._on_seek_started)
        self.slider_progress.sliderReleased.connect(self._on_seek_finished)
        self.slider_progress.sliderMoved.connect(self._on_seek_moved)

        self.lbl_time_total = QLabel("00:00", self.card_playing)
        self.lbl_time_total.setStyleSheet("background: transparent; font-size: 10px; color: #9ca3af; font-family: monospace;")

        progress_layout.addWidget(self.lbl_time_cur)
        progress_layout.addWidget(self.slider_progress)
        progress_layout.addWidget(self.lbl_time_total)
        card_layout.addLayout(progress_layout)

        # Controls Row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Shuffle Button
        self.btn_shuffle = QPushButton(self.card_playing)
        self.btn_shuffle.setIcon(create_svg_icon(SVG_SHUFFLE, stroke_color="#9ca3af", size=15))
        self.btn_shuffle.setIconSize(QSize(15, 15))
        self.btn_shuffle.setFixedSize(28, 28)
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setObjectName("btnPlayerControl")
        self.btn_shuffle.setToolTip("Shuffle Playlist")
        self.btn_shuffle.clicked.connect(self.music_service.toggle_shuffle)
        controls_layout.addWidget(self.btn_shuffle)

        # Prev Track Button
        self.btn_prev = QPushButton(self.card_playing)
        self.btn_prev.setIcon(create_svg_icon(SVG_PREV, stroke_color="#f3f4f6", size=16))
        self.btn_prev.setIconSize(QSize(16, 16))
        self.btn_prev.setFixedSize(30, 30)
        self.btn_prev.setObjectName("btnPlayerControl")
        self.btn_prev.setToolTip("Previous Track")
        self.btn_prev.clicked.connect(self.music_service.prev_track)
        controls_layout.addWidget(self.btn_prev)

        # Main Play / Pause Button
        self.btn_play = QPushButton(self.card_playing)
        self.btn_play.setIcon(create_svg_icon(SVG_PLAY, stroke_color="#ffffff", fill_color="#ffffff", size=18))
        self.btn_play.setIconSize(QSize(18, 18))
        self.btn_play.setFixedSize(38, 38)
        self.btn_play.setObjectName("btnPrimaryIcon")
        self.btn_play.setToolTip("Play / Pause")
        self.btn_play.clicked.connect(self.music_service.toggle_play_pause)
        controls_layout.addWidget(self.btn_play)

        # Next Track Button
        self.btn_next = QPushButton(self.card_playing)
        self.btn_next.setIcon(create_svg_icon(SVG_NEXT, stroke_color="#f3f4f6", size=16))
        self.btn_next.setIconSize(QSize(16, 16))
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setObjectName("btnPlayerControl")
        self.btn_next.setToolTip("Next Track")
        self.btn_next.clicked.connect(self.music_service.next_track)
        controls_layout.addWidget(self.btn_next)

        # Loop Mode Button
        self.btn_loop = QPushButton(self.card_playing)
        self.btn_loop.setIcon(create_svg_icon(SVG_REPEAT, stroke_color="#6366f1", size=15))
        self.btn_loop.setIconSize(QSize(15, 15))
        self.btn_loop.setFixedSize(28, 28)
        self.btn_loop.setObjectName("btnPlayerControl")
        self.btn_loop.setToolTip("Loop Mode: Repeat All")
        self.btn_loop.clicked.connect(self.music_service.cycle_loop_mode)
        controls_layout.addWidget(self.btn_loop)

        card_layout.addLayout(controls_layout)
        music_layout.addWidget(self.card_playing)

        # 2. Search & Stats Header
        search_box = QHBoxLayout()
        search_box.setSpacing(6)

        self.txt_music_search = QLineEdit(self.page_music)
        self.txt_music_search.setPlaceholderText("Search songs by title, artist...")
        self.txt_music_search.textChanged.connect(self._on_search_text_changed)
        search_box.addWidget(self.txt_music_search)

        self.btn_play_all_search = QPushButton("▶ All", self.page_music)
        self.btn_play_all_search.setToolTip("Play all search results back-to-back")
        self.btn_play_all_search.setStyleSheet("""
            QPushButton {
                font-size: 11px; font-weight: bold;
                background: rgba(99, 102, 241, 0.28); color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.5); border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: rgba(99, 102, 241, 0.45); color: #ffffff;
            }
        """)
        self.btn_play_all_search.clicked.connect(self._play_all_search_results)
        self.btn_play_all_search.hide()
        search_box.addWidget(self.btn_play_all_search)

        self.btn_clear_search = QPushButton(self.page_music)
        self.btn_clear_search.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#9ca3af", size=14))
        self.btn_clear_search.setObjectName("btnPlayerControl")
        self.btn_clear_search.setFixedSize(28, 28)
        self.btn_clear_search.setToolTip("Clear Search")
        self.btn_clear_search.clicked.connect(self.txt_music_search.clear)
        search_box.addWidget(self.btn_clear_search)

        music_layout.addLayout(search_box)

        # Active filter state (default is full library, space reclaimed for music list)
        self.active_music_filter = 'all'
        self.filter_buttons = {}

        # 3. Paginated Track List Box
        self.lst_music = QListWidget(self.page_music)
        self.lst_music.setObjectName("lstMusic")
        self.lst_music.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lst_music.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lst_music.setStyleSheet("""
            QListWidget#lstMusic {
                background: rgba(10, 12, 22, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 4px;
            }
            QListWidget#lstMusic::item {
                padding: 6px 8px;
                border-radius: 6px;
                margin-bottom: 3px;
                border: 1px solid transparent;
            }
            QListWidget#lstMusic::item:hover {
                background-color: rgba(99, 102, 241, 0.15);
                border-color: rgba(99, 102, 241, 0.35);
            }
            QListWidget#lstMusic::item:selected {
                background-color: rgba(99, 102, 241, 0.28);
                border-color: #6366f1;
            }
        """)
        self.lst_music.itemDoubleClicked.connect(self._on_track_item_clicked)
        self.lst_music.itemClicked.connect(self._on_track_item_clicked)
        music_layout.addWidget(self.lst_music)

        # 4. Pagination & Library Footer
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(6)

        self.btn_music_prev = QPushButton(" Prev", self.page_music)
        self.btn_music_prev.setIcon(create_svg_icon(SVG_PREV, stroke_color="#f3f4f6", size=12))
        self.btn_music_prev.setObjectName("btnPageNav")
        self.btn_music_prev.clicked.connect(self._prev_music_page)
        pagination_layout.addWidget(self.btn_music_prev)

        self.lbl_music_page_info = QLabel("Page 1 of 1", self.page_music)
        self.lbl_music_page_info.setObjectName("subLabel")
        self.lbl_music_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self.lbl_music_page_info, 1)

        self.btn_music_next = QPushButton("Next ", self.page_music)
        self.btn_music_next.setIcon(create_svg_icon(SVG_NEXT, stroke_color="#f3f4f6", size=12))
        self.btn_music_next.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_music_next.setObjectName("btnPageNav")
        self.btn_music_next.clicked.connect(self._next_music_page)
        pagination_layout.addWidget(self.btn_music_next)

        self.btn_rescan = QPushButton(self.page_music)
        self.btn_rescan.setIcon(create_svg_icon(SVG_REFRESH, stroke_color="#9ca3af", size=14))
        self.btn_rescan.setIconSize(QSize(14, 14))
        self.btn_rescan.setFixedSize(26, 26)
        self.btn_rescan.setObjectName("btnPlayerControl")
        self.btn_rescan.setToolTip("Rescan library (checks ~/Downloads, ~/Music & ETS2 for new songs)")
        self.btn_rescan.clicked.connect(self._on_rescan_clicked)
        pagination_layout.addWidget(self.btn_rescan)

        music_layout.addLayout(pagination_layout)

        self.view_stack.addWidget(self.page_music)

        main_layout.addWidget(self.view_stack)

    def _switch_tab(self, index):
        self._flush_autosave()
        self.view_stack.setCurrentIndex(index)
        if index == 2:
            self._load_music_library()

    def _toggle_board(self):
        OkumBoardManager.get_instance().toggle_board()

    def position_near_orb(self, orb_pos):
        x = orb_pos.x() - 410
        y = orb_pos.y() - 250
        if x < 10:
            x = orb_pos.x() + 94
        if y < 10:
            y = 10
        self.move(x, y)

    def position_near_spider(self, spider_pos):
        self.position_near_orb(spider_pos)

    # Note logic
    def _on_category_button_clicked(self, cat):
        if cat == "Recent":
            self._flush_autosave()
            self.txt_title.hide()
            self.note_body_stack.setCurrentIndex(1)
            self._load_recent_notes()
        else:
            self.txt_title.show()
            self.current_category = cat
            self.note_body_stack.setCurrentIndex(0)
            self._on_note_content_changed()

    def _set_category(self, cat):
        self.txt_title.show()
        self.current_category = cat
        self._on_note_content_changed()

    def _toggle_pin(self, checked):
        self.is_pinned = checked
        self._on_note_content_changed()

    def _load_recent_notes(self):
        query = self.txt_recent_search.text().strip()
        notes = self.db.get_all_notes(search=query)
        self.lst_recent_notes.clear()

        category_colors = {
            'General': ('#a5b4fc', 'rgba(99, 102, 241, 0.25)'),
            'Ideas': ('#67e8f9', 'rgba(6, 182, 212, 0.25)'),
            'Tasks': ('#6ee7b7', 'rgba(16, 185, 129, 0.25)'),
            'Urgent': ('#fca5a5', 'rgba(239, 68, 68, 0.25)'),
        }

        if not notes:
            item = QListWidgetItem()
            lbl = QLabel("<div style='text-align:center; padding: 25px 10px; color: #9ca3af; font-size: 12px;'>No matching notes found</div>")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(340, 60))
            self.lst_recent_notes.addItem(item)
            self.lst_recent_notes.setItemWidget(item, lbl)
            return

        for n in notes:
            pin_icon = '<span style="background: rgba(245, 158, 11, 0.25); color: #fbbf24; font-size: 8px; font-weight: bold; border-radius: 3px; padding: 1px 4px; margin-right: 4px;">PIN</span>' if n.get('pinned') else ""
            title = html.escape(n.get('title') or "Untitled Note")
            snippet = html.escape((n.get('content') or '').strip().replace('\n', ' ')[:75])
            if not snippet:
                snippet = "<i style='color: #6b7280;'>No content</i>"
            
            cat = n.get('category') or "General"
            cat_color, cat_bg = category_colors.get(cat, ('#a5b4fc', 'rgba(99, 102, 241, 0.25)'))

            card_html = f"""
            <div style="line-height: 1.3;">
                <div style="font-weight: bold; font-size: 12px; color: #ffffff; margin-bottom: 3px;">
                    {pin_icon}{title} <span style="background: {cat_bg}; color: {cat_color}; font-size: 9px; font-weight: bold; border-radius: 4px; padding: 1px 5px; margin-left: 4px;">{cat}</span>
                </div>
                <div style="font-size: 11px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {snippet}
                </div>
            </div>
            """
            lbl = QLabel(card_html)
            lbl.setStyleSheet("background: transparent;")
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, n['id'])
            item.setSizeHint(QSize(340, 58))
            self.lst_recent_notes.addItem(item)
            self.lst_recent_notes.setItemWidget(item, lbl)

    def _on_recent_note_selected(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if note_id:
            self.load_note(note_id)

    def _update_note_status(self):
        content = self.txt_content.toPlainText()
        title = self.txt_title.text()
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        self.lbl_words.setText(f"{words} words • {chars} chars")

        has_text = bool(title.strip() or content.strip())

        if not has_text:
            # 1. Red: Note area is empty (0 words 0 chars)
            self.lbl_save_dot.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: bold;")
            self.lbl_save_dot.setToolTip("Empty Note (0 words)")
        elif self.current_note_id is None:
            # 2. Yellow: There is text but the new note has not been saved yet
            self.lbl_save_dot.setStyleSheet("color: #f59e0b; font-size: 13px; font-weight: bold;")
            self.lbl_save_dot.setToolTip("Unsaved New Note")
        else:
            # Check if there are new additions or edits not yet saved
            is_modified = (
                title.strip() != self._saved_snapshot.get('title', '').strip() or
                content.strip() != self._saved_snapshot.get('content', '').strip() or
                self.current_category != self._saved_snapshot.get('category', 'General') or
                self.is_pinned != self._saved_snapshot.get('pinned', False)
            )
            if is_modified:
                # 4. Purple: New additions / changes on existing note have not been saved
                self.lbl_save_dot.setStyleSheet("color: #a855f7; font-size: 13px; font-weight: bold;")
                self.lbl_save_dot.setToolTip("Unsaved Changes (Modified)")
            else:
                # 3. Green: Note is saved and up to date
                self.lbl_save_dot.setStyleSheet("color: #10b981; font-size: 13px; font-weight: bold;")
                self.lbl_save_dot.setToolTip("Note Saved")

    def _on_note_content_changed(self):
        self._update_note_status()
        title = self.txt_title.text().strip()
        content = self.txt_content.toPlainText().strip()
        if title or content:
            # Debounced auto-save triggers 600ms after user stops typing
            self.autosave_timer.start(600)

    def _perform_autosave(self):
        title = self.txt_title.text().strip()
        content = self.txt_content.toPlainText().strip()
        if not title and not content:
            return
        self.save_note()

    def _flush_autosave(self):
        if hasattr(self, 'autosave_timer') and self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

    def new_note(self):
        self._flush_autosave()
        self.current_note_id = None
        self.current_category = "General"
        self.is_pinned = False
        self._saved_snapshot = {
            'title': '',
            'content': '',
            'category': 'General',
            'pinned': False
        }
        self.txt_title.show()
        self.txt_title.clear()
        self.txt_content.clear()
        self.btn_pin.setChecked(False)
        for btn in self.cat_group.buttons():
            if btn.text() == "General":
                btn.setChecked(True)
                break
        self.note_body_stack.setCurrentIndex(0)
        self._update_note_status()
        self.txt_title.setFocus()

    def load_note(self, note_id):
        self._flush_autosave()
        note = self.db.get_note(note_id)
        if not note:
            return

        self.current_note_id = note['id']
        self.current_category = note['category']
        self.is_pinned = bool(note['pinned'])
        self._saved_snapshot = {
            'title': note['title'],
            'content': note['content'],
            'category': note['category'],
            'pinned': bool(note['pinned'])
        }
        self.txt_title.show()
        self.txt_title.setText(note['title'])
        self.txt_content.setText(note['content'])
        self.btn_pin.setChecked(self.is_pinned)

        found_btn = False
        for btn in self.cat_group.buttons():
            if btn.text() == self.current_category:
                btn.setChecked(True)
                found_btn = True
                break
        if not found_btn:
            for btn in self.cat_group.buttons():
                if btn.text() == "General":
                    btn.setChecked(True)
                    break

        self.note_body_stack.setCurrentIndex(0)
        self._update_note_status()

    def save_note(self):
        if hasattr(self, 'autosave_timer') and self.autosave_timer.isActive():
            self.autosave_timer.stop()

        title = self.txt_title.text().strip()
        content = self.txt_content.toPlainText().strip()
        if not title and not content:
            return

        note_id = self.db.save_note({
            'id': self.current_note_id,
            'title': title or "Untitled Note",
            'category': self.current_category,
            'content': content,
            'pinned': self.is_pinned
        })
        self.current_note_id = note_id
        self._saved_snapshot = {
            'title': title or "Untitled Note",
            'content': content,
            'category': self.current_category,
            'pinned': self.is_pinned
        }
        self._update_note_status()

    # Chat / Ask Okum logic
    def _init_ai_provider(self):
        self.db.set_setting('ai_provider', 'groq')
        self._update_brain_header_indicator('groq')

    def _on_ai_provider_changed(self, index):
        self._update_brain_header_indicator('groq')

    def _update_brain_header_indicator(self, provider='groq'):
        self.lbl_sub.setText("● Brain: Groq AI (Active)")
        self.lbl_sub.setStyleSheet("color: #38bdf8; font-weight: 500; font-size: 10px;")

    def _clear_current_chat(self):
        if self.active_session:
            self.db.delete_chat_session(self.active_session['id'])
            self.active_session = None
        self._load_active_chat_session()

    def _load_active_chat_session(self):
        self.active_session = self.db.get_or_create_active_session()
        self._refresh_chat_display()

    def _refresh_chat_display(self):
        self.lst_chat.clear()
        if not self.active_session:
            return

        messages = self.db.get_chat_messages(self.active_session['id'])
        if not messages:
            self._append_message_bubble("assistant", "Hello! I am Okum, your AI assistant. You can use local offline AI or fast online Groq via the selector above. What can I do for you?")
        else:
            for msg in messages:
                self._append_message_bubble(msg['sender'], msg['content'])

    def _append_message_bubble(self, sender, text):
        is_user = sender == 'user'
        align_html = "right" if is_user else "left"
        name_tag = "You" if is_user else "Okum"
        name_color = "#a5b4fc" if is_user else "#38bdf8"

        formatted_body = format_chat_text(text)

        html = f"""
        <div style="text-align: {align_html}; margin-bottom: 2px;">
            <div style="font-size: 11px; font-weight: bold; color: {name_color}; margin-bottom: 3px;">{name_tag}</div>
            <div style="text-align: left; background: transparent; color: #f3f4f6; font-size: 13px; word-wrap: break-word; white-space: normal;">
                {formatted_body}
            </div>
        </div>
        """

        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setFixedWidth(350)
        lbl.setContentsMargins(0, 0, 0, 4)

        # Accurate layout height calculation with Inter font metrics & document margins to prevent any vertical clipping
        doc = QTextDocument()
        doc.setDefaultFont(QFont('Inter', 10))
        doc.setDocumentMargin(4)
        doc.setHtml(html)
        doc.setTextWidth(350)
        calc_height = int(doc.documentLayout().documentSize().height()) + 24

        item = QListWidgetItem()
        item.setSizeHint(QSize(350, max(calc_height, 40)))
        self.lst_chat.addItem(item)
        self.lst_chat.setItemWidget(item, lbl)
        self.lst_chat.scrollToBottom()

    def _insert_chip(self, prefix):
        self.btn_tab_ask.setChecked(True)
        self.view_stack.setCurrentIndex(1)
        self.txt_prompt.setText(prefix)
        self.txt_prompt.setFocus()

    def _send_question(self):
        prompt = self.txt_prompt.text().strip()
        if not prompt:
            return

        self.txt_prompt.clear()
        self._append_message_bubble("user", prompt)

        if not self.active_session:
            self.active_session = self.db.get_or_create_active_session()

        # Save user prompt to DB
        self.db.save_chat_message(self.active_session['id'], "user", prompt)

        provider = "groq"
        self.lbl_thinking.setText("Okum is querying Groq Cloud (llama-3.3-70b)...")
        self.lbl_thinking.show()
        self.txt_prompt.setEnabled(False)
        self.btn_send.setEnabled(False)

        # Launch async AI thread
        self.current_worker = AIQueryWorker(prompt, self.active_session['id'], provider=provider)
        self.current_worker.response_ready.connect(self._on_query_success)
        self.current_worker.error_occurred.connect(self._on_query_error)
        self.current_worker.start()

    def _on_query_success(self, response_text, session_id, prompt):
        self.lbl_thinking.hide()
        self.txt_prompt.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.txt_prompt.setFocus()

        self.db.save_chat_message(session_id, "assistant", response_text)
        self._append_message_bubble("assistant", response_text)

    def _on_query_error(self, err_msg, session_id):
        self.lbl_thinking.hide()
        self.txt_prompt.setEnabled(True)
        self.btn_send.setEnabled(True)

        err_text = f"Warning: {err_msg}"
        self._append_message_bubble("assistant", err_text)

    # Music Player Logic
    def _bind_music_signals(self):
        self.music_service.track_changed.connect(self._on_track_changed)
        self.music_service.state_changed.connect(self._on_play_state_changed)
        self.music_service.position_changed.connect(self._on_position_changed)
        self.music_service.duration_changed.connect(self._on_duration_changed)
        self.music_service.mode_changed.connect(self._on_mode_changed)
        self.music_service.library_scanned.connect(self._on_library_scanned)
        self.music_service.track_unavailable.connect(self._on_track_unavailable)
        self.music_service.error_occurred.connect(self._on_player_error_occurred)
        self.music_service.queue_changed.connect(self._on_queue_changed)
        self.music_service.favorite_changed.connect(self._on_favorite_changed)

        if self.music_service.current_track:
            self._on_track_changed(self.music_service.current_track)
        else:
            self._on_track_changed(None)

    def _on_queue_changed(self, count):
        if count > 0:
            self.btn_queue_badge.setText(f"Up Next: {count} ✕")
            self.btn_queue_badge.show()
        else:
            self.btn_queue_badge.hide()

    def _on_favorite_changed(self, filepath, is_fav):
        if self.music_service.current_track and self.music_service.current_track.get('filepath') == filepath:
            self.btn_now_playing_fav.setText("❤️" if is_fav else "♡")
            self.btn_now_playing_fav.setStyleSheet(f"background: transparent; border: none; font-size: 14px; color: {'#ec4899' if is_fav else '#9ca3af'};")

        # If currently filtered by favorites, refresh view
        if getattr(self, 'active_music_filter', 'all') == 'favorites':
            self._load_music_library()

    def _on_toggle_current_favorite(self):
        is_fav = self.music_service.toggle_favorite()
        self.btn_now_playing_fav.setText("❤️" if is_fav else "♡")
        self.btn_now_playing_fav.setStyleSheet(f"background: transparent; border: none; font-size: 14px; color: {'#ec4899' if is_fav else '#9ca3af'};")

    def _get_chip_style(self, is_active):
        if is_active:
            return """
                QPushButton {
                    background: rgba(99, 102, 241, 0.35);
                    border: 1px solid rgba(129, 140, 248, 0.65);
                    border-radius: 11px;
                    color: #ffffff;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                }
            """
        else:
            return """
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 11px;
                    color: #9ca3af;
                    font-size: 10px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #f3f4f6;
                    border-color: rgba(255, 255, 255, 0.2);
                }
            """

    def _on_filter_chip_clicked(self, fid):
        # One-tap clear: tapping active chip again resets to 'all'
        if self.active_music_filter == fid and fid != 'all':
            self.active_music_filter = 'all'
        else:
            self.active_music_filter = fid

        for f_key, btn in self.filter_buttons.items():
            is_active = (f_key == self.active_music_filter)
            btn.setChecked(is_active)
            btn.setStyleSheet(self._get_chip_style(is_active))

        self.music_page = 1
        self._load_music_library()

    def _play_all_search_results(self):
        query = self.txt_music_search.text().strip()
        if not query:
            return
        all_results = self.db.get_all_tracks_for_playback(query=query, filter_type=self.active_music_filter)
        if all_results:
            self.music_service.play_track(all_results[0], playlist=all_results)

    def _on_track_unavailable(self, track_dict, reason):
        self.lbl_music_status_pill.setText("File Skipped")
        self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(239, 68, 68, 0.25); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 2px 6px;")
        self._load_music_library()

    def _on_player_error_occurred(self, err_msg):
        if self.music_service.current_track:
            self.lbl_music_status_pill.setText("Paused")
            self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(245, 158, 11, 0.25); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px; padding: 2px 6px;")

    def _load_music_library(self):
        query = self.txt_music_search.text().strip()
        f_type = getattr(self, 'active_music_filter', 'all')
        self.total_music_count = self.db.get_music_tracks_count(query, filter_type=f_type)
        self.total_music_pages = max(1, (self.total_music_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        
        if self.music_page > self.total_music_pages:
            self.music_page = self.total_music_pages
        if self.music_page < 1:
            self.music_page = 1

        # Show/hide "Play All" button for search results
        if query and self.total_music_count > 0:
            self.btn_play_all_search.setText(f"▶ All ({self.total_music_count})")
            self.btn_play_all_search.show()
        else:
            self.btn_play_all_search.hide()

        offset = (self.music_page - 1) * self.PAGE_SIZE
        self.current_displayed_tracks = self.db.search_music_tracks(query, filter_type=f_type, limit=self.PAGE_SIZE, offset=offset)

        self.lst_music.clear()
        curr_p = self.music_service.current_track.get('filepath') if self.music_service.current_track else None

        for track in self.current_displayed_tracks:
            item_widget = self._create_track_row_widget(track, curr_p)
            item = QListWidgetItem()
            item.setSizeHint(QSize(340, 46))
            item.setData(Qt.ItemDataRole.UserRole, track)
            self.lst_music.addItem(item)
            self.lst_music.setItemWidget(item, item_widget)

            if curr_p and track.get('filepath') == curr_p:
                self.lst_music.setCurrentItem(item)

        # Update page navigation state
        self.lbl_music_page_info.setText(f"Page {self.music_page} of {self.total_music_pages} ({self.total_music_count:,} songs)")
        self.btn_music_prev.setEnabled(self.music_page > 1)
        self.btn_music_next.setEnabled(self.music_page < self.total_music_pages)

    def _create_track_row_widget(self, track, curr_p):
        is_playing = bool(curr_p and track.get('filepath') == curr_p)
        fp = track.get('filepath', '')

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        # Micro Album Art Thumbnail (32x32)
        lbl_art = QLabel(widget)
        lbl_art.setFixedSize(32, 32)
        lbl_art.setStyleSheet("border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.08);")
        lbl_art.setScaledContents(True)
        lbl_art.setPixmap(CoverArtCache.get_cover_pixmap(fp, size=32))
        layout.addWidget(lbl_art)

        # Title & Artist Text Column
        col = QVBoxLayout()
        col.setSpacing(1)
        col.setContentsMargins(0, 0, 0, 0)

        raw_title = (track.get('title') or '').strip()
        if not raw_title:
            raw_title = os.path.splitext(track.get('filename') or '')[0].replace('_', ' ')
        raw_artist = (track.get('artist') or '').strip() or "Local Music"
        play_count = track.get('play_count', 0) or 0
        plays_str = f" • {play_count} {'play' if play_count == 1 else 'plays'}" if play_count > 0 else ""

        lbl_title = QLabel(raw_title, widget)
        title_color = "#a5b4fc" if is_playing else "#f3f4f6"
        lbl_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {title_color};")
        lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        lbl_artist = QLabel(f"{raw_artist}{plays_str}", widget)
        lbl_artist.setStyleSheet("font-size: 10px; color: #9ca3af;")
        lbl_artist.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        col.addWidget(lbl_title)
        col.addWidget(lbl_artist)
        layout.addLayout(col, 1)

        # Duration
        dur_str = format_time_ms(track.get('duration', 0)) if track.get('duration') else ""
        if dur_str and dur_str != "00:00":
            lbl_dur = QLabel(dur_str, widget)
            lbl_dur.setStyleSheet("font-size: 10px; color: #6b7280; font-family: monospace;")
            lbl_dur.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(lbl_dur)

        # Up Next "+" Button
        btn_add = QPushButton("+", widget)
        btn_add.setFixedSize(22, 22)
        btn_add.setToolTip("Play Next (Add to Queue)")
        btn_add.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                color: #d1d5db;
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background: rgba(99, 102, 241, 0.35);
                border-color: #6366f1;
                color: #ffffff;
            }
        """)
        btn_add.clicked.connect(lambda checked, t=track: self.music_service.add_to_up_next(t))
        layout.addWidget(btn_add)

        # Heart Favorite Button
        is_fav = bool(track.get('is_favorite', 0))
        btn_fav = QPushButton("❤️" if is_fav else "♡", widget)
        btn_fav.setFixedSize(22, 22)
        btn_fav.setToolTip("Toggle Favorite")
        btn_fav.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 12px;
                color: {'#ec4899' if is_fav else '#6b7280'};
            }}
            QPushButton:hover {{
                color: #ec4899;
            }}
        """)
        btn_fav.clicked.connect(lambda checked, t=track, b=btn_fav: self._toggle_track_fav_row(t, b))
        layout.addWidget(btn_fav)

        return widget

    def _toggle_track_fav_row(self, track, btn):
        is_fav = self.music_service.toggle_favorite(track)
        btn.setText("❤️" if is_fav else "♡")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 12px;
                color: {'#ec4899' if is_fav else '#6b7280'};
            }}
            QPushButton:hover {{
                color: #ec4899;
            }}
        """)

    def _on_search_text_changed(self, text):
        self.music_page = 1
        self._load_music_library()

    def _prev_music_page(self):
        if self.music_page > 1:
            self.music_page -= 1
            self._load_music_library()

    def _next_music_page(self):
        if self.music_page < self.total_music_pages:
            self.music_page += 1
            self._load_music_library()

    def _on_track_item_clicked(self, item):
        track_data = item.data(Qt.ItemDataRole.UserRole)
        if not track_data:
            return

        query = self.txt_music_search.text().strip()
        if query:
            # Single search result requested: plays once, resumes main collection when done!
            self.music_service.play_track(track_data, is_single_request=True)
        else:
            # Human is browsing: pass all tracks for active filter so shuffle has the full cosmic library pool!
            pool = self.db.get_all_tracks_for_playback(filter_type=getattr(self, 'active_music_filter', 'all'))
            self.music_service.play_track(track_data, playlist=pool)

    def _on_track_changed(self, track):
        if not track:
            self.lbl_music_track.setText("No track playing")
            self.lbl_music_artist.setText("Quick Play • Ready")
            self.lbl_cover_art.setPixmap(CoverArtCache.get_default_pixmap(50))
            self.card_playing.set_wallpaper_pixmap(CoverArtCache.get_hero_wallpaper(None))
            self.btn_now_playing_fav.setText("♡")
            return

        title = track.get('title') or track.get('filename')
        artist = track.get('artist') or "Unknown Artist"
        fp = track.get('filepath', '')

        self.lbl_music_track.setText(title)
        self.lbl_music_artist.setText(f"{artist} • {track.get('ext', '')}")
        self.lbl_music_status_pill.setText("Playing")
        self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.25); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 2px 6px;")

        # Update Cover Art Thumbnail & Low-Blur Transparent Wallpaper
        self.lbl_cover_art.setPixmap(CoverArtCache.get_cover_pixmap(fp, size=50))
        self.card_playing.set_wallpaper_pixmap(CoverArtCache.get_hero_wallpaper(fp))

        # Update Favorite Heart Button
        is_fav = self.music_service.is_favorite(fp)
        self.btn_now_playing_fav.setText("❤️" if is_fav else "♡")
        self.btn_now_playing_fav.setStyleSheet(f"background: transparent; border: none; font-size: 14px; color: {'#ec4899' if is_fav else '#9ca3af'};")

        # Highlight in current visible list
        for i in range(self.lst_music.count()):
            item = self.lst_music.item(i)
            t = item.data(Qt.ItemDataRole.UserRole)
            if t and t.get('filepath') == fp:
                self.lst_music.setCurrentItem(item)
                break

    def _on_play_state_changed(self, is_playing):
        if is_playing:
            self.btn_play.setIcon(create_svg_icon(SVG_PAUSE, stroke_color="#ffffff", fill_color="#ffffff", size=18))
            self.lbl_music_status_pill.setText("Playing")
            self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.25); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 2px 6px;")
        else:
            self.btn_play.setIcon(create_svg_icon(SVG_PLAY, stroke_color="#ffffff", fill_color="#ffffff", size=18))
            if self.music_service.current_track:
                self.lbl_music_status_pill.setText("Paused")
                self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(245, 158, 11, 0.25); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px; padding: 2px 6px;")

    def _on_position_changed(self, pos_ms, duration_ms):
        if not self._user_seeking:
            if duration_ms > 0:
                self.slider_progress.setRange(0, duration_ms)
                self.slider_progress.setValue(pos_ms)
            else:
                self.slider_progress.setValue(0)
            self.lbl_time_cur.setText(format_time_ms(pos_ms))
            self.lbl_time_total.setText(format_time_ms(duration_ms))

    def _on_duration_changed(self, duration_ms):
        self.slider_progress.setRange(0, duration_ms)
        self.lbl_time_total.setText(format_time_ms(duration_ms))

    def _on_seek_started(self):
        self._user_seeking = True

    def _on_seek_moved(self, val):
        self.lbl_time_cur.setText(format_time_ms(val))

    def _on_seek_finished(self):
        self._user_seeking = False
        self.music_service.seek(self.slider_progress.value())

    def _on_mode_changed(self, loop_mode, is_shuffle):
        # Update shuffle button style
        self.btn_shuffle.setChecked(is_shuffle)
        stroke = "#a5b4fc" if is_shuffle else "#9ca3af"
        self.btn_shuffle.setIcon(create_svg_icon(SVG_SHUFFLE, stroke_color=stroke, size=15))

        # Update loop mode icon and tooltip
        if loop_mode == "one":
            self.btn_loop.setIcon(create_svg_icon(SVG_REPEAT_ONE, stroke_color="#6366f1", size=15))
            self.btn_loop.setToolTip("Loop Mode: Repeat Track")
            self.btn_loop.setStyleSheet("border-color: #6366f1; background: rgba(99, 102, 241, 0.3);")
        elif loop_mode == "all":
            self.btn_loop.setIcon(create_svg_icon(SVG_REPEAT, stroke_color="#6366f1", size=15))
            self.btn_loop.setToolTip("Loop Mode: Repeat All")
            self.btn_loop.setStyleSheet("border-color: #6366f1; background: rgba(99, 102, 241, 0.3);")
        else: # none
            self.btn_loop.setIcon(create_svg_icon(SVG_REPEAT, stroke_color="#6b7280", size=15))
            self.btn_loop.setToolTip("Loop Mode: Off")
            self.btn_loop.setStyleSheet("")

    def _on_rescan_clicked(self):
        self.lbl_music_status_pill.setText("Scanning...")
        self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(56, 189, 248, 0.25); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 6px; padding: 2px 6px;")
        self.music_service.scan_library_fast()

    def _on_library_scanned(self, total_count):
        self._load_music_library()
        if self.music_service.current_track and hasattr(self.music_service, 'player') and self.music_service.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.lbl_music_status_pill.setText("Playing")
            self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.25); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 2px 6px;")
        elif self.music_service.current_track:
            self.lbl_music_status_pill.setText("Paused")
            self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(245, 158, 11, 0.25); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px; padding: 2px 6px;")
        else:
            self.lbl_music_status_pill.setText("Ready")
            self.lbl_music_status_pill.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(99, 102, 241, 0.25); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; padding: 2px 6px;")

    def _on_expand_dashboard(self):
        self.hide()
        self.open_dashboard_callback()

    def _open_floating_mini_player(self):
        from ui.floating_music_window import FloatingMusicWindow
        self.hide()
        FloatingMusicWindow.get_instance(self._restore_from_mini_player).show_player()

    def _restore_from_mini_player(self):
        self.tab_group.button(2).setChecked(True)
        self._switch_tab(2)
        self.show()
        self.raise_()
        self.activateWindow()

# Alias for backwards compatibility
QuickNotepad = QuickWindow
