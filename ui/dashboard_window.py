from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QSize, QByteArray
from PyQt6.QtGui import QTextDocument, QFont, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QListWidget, QListWidgetItem,
    QStackedWidget, QComboBox, QFrame, QFileDialog, QMessageBox
)
from services.ai_service import AIQueryWorker, OllamaQueryWorker, is_ollama_running
from ui.quick_window import format_chat_text

def create_dash_svg_icon(svg_inner, stroke_color='#f3f4f6', fill_color='none', size=16, stroke_width=2):
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

SVG_NOTE = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'
SVG_CHAT = '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
SVG_SUN = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
SVG_CLOCK = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
SVG_SETTINGS = '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
SVG_TRASH = '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'

class DashboardWindow(QMainWindow):
    def __init__(self, db, open_notepad_callback):
        super().__init__()
        self.db = db
        self.open_notepad_callback = open_notepad_callback
        self.selected_session_id = None
        self.dash_worker = None

        self.setWindowTitle("Okum — Personal Assistant Dashboard")
        self.setFixedSize(850, 560)
        self.setObjectName("DashboardWindow")

        self._init_ui()
        self._load_notes()

    def showEvent(self, event):
        super().showEvent(event)
        self.combo_cat.setCurrentIndex(0) # 'ALL'
        self.txt_search.clear()
        self._load_notes()
        self._load_chat_sessions()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Panel
        sidebar = QFrame(self)
        sidebar.setStyleSheet("background-color: rgba(10, 13, 23, 0.95); border-right: 1px solid rgba(255, 255, 255, 0.08);")
        sidebar.setFixedWidth(200)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(10)

        # Brand Header
        lbl_brand = QLabel("<b>Okum</b> <span style='font-size:10px; color:#6366f1;'>v1.0</span>", self)
        lbl_brand.setStyleSheet("font-size: 18px; color: #ffffff;")
        lbl_sub = QLabel("Assistant for <b>mphatic</b>", self)
        lbl_sub.setStyleSheet("font-size: 11px; color: #06b6d4;")

        sidebar_layout.addWidget(lbl_brand)
        sidebar_layout.addWidget(lbl_sub)
        sidebar_layout.addSpacing(20)

        # Nav Buttons with SVG Icons
        self.btn_nav_notes = QPushButton("  All Notes", self)
        self.btn_nav_notes.setIcon(create_dash_svg_icon(SVG_NOTE, stroke_color="#a5b4fc", size=16))
        self.btn_nav_chats = QPushButton("  Chat History", self)
        self.btn_nav_chats.setIcon(create_dash_svg_icon(SVG_CHAT, stroke_color="#a5b4fc", size=16))
        self.btn_nav_briefing = QPushButton("  Briefing", self)
        self.btn_nav_briefing.setIcon(create_dash_svg_icon(SVG_SUN, stroke_color="#a5b4fc", size=16))
        self.btn_nav_focus = QPushButton("  Focus Mode", self)
        self.btn_nav_focus.setIcon(create_dash_svg_icon(SVG_CLOCK, stroke_color="#a5b4fc", size=16))
        self.btn_nav_settings = QPushButton("  Settings", self)
        self.btn_nav_settings.setIcon(create_dash_svg_icon(SVG_SETTINGS, stroke_color="#a5b4fc", size=16))

        nav_btns = [
            self.btn_nav_notes,
            self.btn_nav_chats,
            self.btn_nav_briefing,
            self.btn_nav_focus,
            self.btn_nav_settings
        ]
        for idx, btn in enumerate(nav_btns):
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        lbl_offline = QLabel("● 100% Offline LLM", self)
        lbl_offline.setStyleSheet("font-size: 11px; color: #10b981;")
        sidebar_layout.addWidget(lbl_offline)

        main_layout.addWidget(sidebar)

        # 2. Main Content Area (Stacked Widget)
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        # TAB 0: ALL NOTES
        self.tab_notes = QWidget()
        notes_layout = QVBoxLayout(self.tab_notes)
        notes_layout.setContentsMargins(24, 20, 24, 20)
        notes_layout.setSpacing(14)

        top_bar = QHBoxLayout()
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("Search notes by title or content...")
        self.txt_search.textChanged.connect(self._load_notes)
        top_bar.addWidget(self.txt_search)

        self.combo_cat = QComboBox(self)
        self.combo_cat.addItems(["ALL", "General", "Ideas", "Tasks", "Urgent"])
        self.combo_cat.currentTextChanged.connect(self._load_notes)
        top_bar.addWidget(self.combo_cat)

        self.btn_new = QPushButton("+ Take Note", self)
        self.btn_new.setObjectName("btnPrimary")
        self.btn_new.clicked.connect(self._on_create_note)
        top_bar.addWidget(self.btn_new)

        notes_layout.addLayout(top_bar)

        self.lst_notes = QListWidget(self)
        self.lst_notes.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { background: rgba(22, 27, 46, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; margin-bottom: 8px; padding: 12px; }
            QListWidget::item:hover { background: rgba(99, 102, 241, 0.15); border-color: #6366f1; }
        """)
        self.lst_notes.itemDoubleClicked.connect(self._on_note_double_clicked)
        notes_layout.addWidget(self.lst_notes)

        self.stack.addWidget(self.tab_notes)

        # TAB 1: CHAT HISTORY
        self.tab_chats = QWidget()
        chats_layout = QHBoxLayout(self.tab_chats)
        chats_layout.setContentsMargins(16, 16, 16, 16)
        chats_layout.setSpacing(14)

        # Left Column: Sessions List
        session_col = QVBoxLayout()
        session_col.setSpacing(10)

        lbl_s_head = QLabel("<b>Conversations</b>", self)
        lbl_s_head.setStyleSheet("font-size: 14px; color: #ffffff;")
        session_col.addWidget(lbl_s_head)

        s_btn_box = QHBoxLayout()
        self.btn_new_chat = QPushButton("+ New Chat", self)
        self.btn_new_chat.setObjectName("btnPrimary")
        self.btn_new_chat.clicked.connect(self._create_new_chat_session)
        s_btn_box.addWidget(self.btn_new_chat)

        self.btn_clear_chats = QPushButton(self)
        self.btn_clear_chats.setIcon(create_dash_svg_icon(SVG_TRASH, stroke_color="#f87171", size=16))
        self.btn_clear_chats.setObjectName("btnDanger")
        self.btn_clear_chats.setToolTip("Clear All Chat History")
        self.btn_clear_chats.setFixedSize(32, 32)
        self.btn_clear_chats.clicked.connect(self._clear_all_chats)
        s_btn_box.addWidget(self.btn_clear_chats)

        session_col.addLayout(s_btn_box)

        self.lst_sessions = QListWidget(self)
        self.lst_sessions.setFixedWidth(220)
        self.lst_sessions.setStyleSheet("""
            QListWidget { background: rgba(10, 12, 22, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; }
            QListWidget::item { padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QListWidget::item:selected { background: rgba(99, 102, 241, 0.25); border-left: 3px solid #6366f1; }
        """)
        self.lst_sessions.itemClicked.connect(self._on_session_selected)
        session_col.addWidget(self.lst_sessions)

        chats_layout.addLayout(session_col)

        # Right Column: Thread Messages & Input
        thread_col = QVBoxLayout()
        thread_col.setSpacing(10)

        # Thread Header with Title and AI Engine Dropdown
        thread_header = QHBoxLayout()
        thread_header.setSpacing(8)

        self.lbl_chat_title = QLabel("Select a session", self)
        self.lbl_chat_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #6366f1;")
        thread_header.addWidget(self.lbl_chat_title)
        thread_header.addStretch()

        lbl_engine = QLabel("Engine:", self)
        lbl_engine.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        thread_header.addWidget(lbl_engine)

        self.combo_dash_ai = QComboBox(self)
        self.combo_dash_ai.addItem("⚡ Local (qwen2.5:1.5b)", "local")
        self.combo_dash_ai.addItem("🌐 Online (Groq Cloud)", "groq")
        self.combo_dash_ai.setStyleSheet("""
            QComboBox {
                background: rgba(22, 27, 46, 0.9);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 6px;
                padding: 2px 8px;
                color: #f3f4f6;
                font-size: 11px;
                min-height: 22px;
            }
            QComboBox:hover { border-color: #6366f1; }
            QComboBox::drop-down { border: none; width: 16px; }
            QComboBox QAbstractItemView {
                background: #111827;
                border: 1px solid rgba(99, 102, 241, 0.5);
                selection-background-color: #4f46e5;
                color: #ffffff;
                padding: 4px;
            }
        """)
        saved_provider = self.db.get_setting('ai_provider', 'local')
        idx = self.combo_dash_ai.findData(saved_provider)
        if idx >= 0:
            self.combo_dash_ai.setCurrentIndex(idx)
        self.combo_dash_ai.currentIndexChanged.connect(self._on_dash_ai_changed)
        thread_header.addWidget(self.combo_dash_ai)

        thread_col.addLayout(thread_header)

        self.lst_dash_messages = QListWidget(self)
        self.lst_dash_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lst_dash_messages.setStyleSheet("""
            QListWidget { background: transparent; border: none; padding: 6px; }
            QListWidget::item { margin-bottom: 8px; background: transparent; border: none; }
        """)
        thread_col.addWidget(self.lst_dash_messages)

        self.lbl_dash_thinking = QLabel("", self)
        self.lbl_dash_thinking.setStyleSheet("font-size: 11px; color: #8b5cf6; font-style: italic;")
        self.lbl_dash_thinking.hide()
        thread_col.addWidget(self.lbl_dash_thinking)

        dash_input_row = QHBoxLayout()
        self.txt_dash_prompt = QLineEdit(self)
        self.txt_dash_prompt.setPlaceholderText("Continue asking Okum (qwen2.5:1.5b)...")
        self.txt_dash_prompt.returnPressed.connect(self._send_dash_question)
        dash_input_row.addWidget(self.txt_dash_prompt)

        self.btn_dash_send = QPushButton("Send", self)
        self.btn_dash_send.setObjectName("btnPrimary")
        self.btn_dash_send.clicked.connect(self._send_dash_question)
        dash_input_row.addWidget(self.btn_dash_send)

        thread_col.addLayout(dash_input_row)

        chats_layout.addLayout(thread_col)

        self.stack.addWidget(self.tab_chats)

        # TAB 2: BRIEFING
        self.tab_briefing = QWidget()
        briefing_layout = QVBoxLayout(self.tab_briefing)
        briefing_layout.setContentsMargins(32, 32, 32, 32)
        briefing_layout.setSpacing(16)

        self.lbl_greeting = QLabel("Hello, mphatic!", self)
        self.lbl_greeting.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff;")
        self.lbl_clock = QLabel("", self)
        self.lbl_clock.setStyleSheet("font-size: 18px; color: #6366f1; font-family: monospace;")
        self.lbl_quote = QLabel('"The secret of getting ahead is getting started."', self)
        self.lbl_quote.setStyleSheet("font-size: 14px; font-style: italic; color: #9ca3af;")

        briefing_layout.addWidget(self.lbl_greeting)
        briefing_layout.addWidget(self.lbl_clock)
        briefing_layout.addWidget(self.lbl_quote)
        briefing_layout.addStretch()

        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self._update_clock)
        self.timer_clock.start(1000)
        self._update_clock()

        self.stack.addWidget(self.tab_briefing)

        # TAB 3: FOCUS TIMER
        self.tab_focus = QWidget()
        focus_layout = QVBoxLayout(self.tab_focus)
        focus_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        focus_layout.setSpacing(20)

        lbl_f_title = QLabel("Focus Mode", self)
        lbl_f_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.lbl_timer = QLabel("25:00", self)
        self.lbl_timer.setStyleSheet("font-size: 56px; font-weight: bold; color: #6366f1; font-family: monospace;")

        btn_box = QHBoxLayout()
        self.btn_timer_start = QPushButton("Start Focus", self)
        self.btn_timer_start.setObjectName("btnPrimary")
        self.btn_timer_start.clicked.connect(self._toggle_focus_timer)
        btn_box.addWidget(self.btn_timer_start)

        focus_layout.addWidget(lbl_f_title)
        focus_layout.addWidget(self.lbl_timer)
        focus_layout.addLayout(btn_box)

        self._focus_running = False
        self._focus_seconds = 25 * 60
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._tick_focus_timer)

        self.stack.addWidget(self.tab_focus)

        # TAB 4: SETTINGS
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout(self.tab_settings)
        settings_layout.setContentsMargins(32, 32, 32, 32)
        settings_layout.setSpacing(16)

        lbl_s_title = QLabel("Settings & Backup", self)
        lbl_s_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        settings_layout.addWidget(lbl_s_title)

        btn_export = QPushButton("Export All Notes (JSON Backup)", self)
        btn_export.clicked.connect(self._export_json)
        settings_layout.addWidget(btn_export)

        btn_open_folder = QPushButton("Open ~/Documents/OkumNotes Folder", self)
        btn_open_folder.clicked.connect(self._open_md_folder)
        settings_layout.addWidget(btn_open_folder)

        settings_layout.addStretch()
        self.stack.addWidget(self.tab_settings)

    def _switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self._load_chat_sessions()

    def _update_clock(self):
        now = datetime.now()
        hours = now.hour
        greeting = "Good Morning"
        if 12 <= hours < 17:
            greeting = "Good Afternoon"
        elif hours >= 17 or hours < 5:
            greeting = "Good Evening"

        self.lbl_greeting.setText(f"{greeting}, mphatic!")
        self.lbl_clock.setText(now.strftime("%A, %b %d, %Y — %I:%M:%S %p"))

    def _load_notes(self):
        self.lst_notes.clear()
        search = self.txt_search.text().strip()
        cat = self.combo_cat.currentText()

        notes = self.db.get_all_notes(category=cat, search=search)
        for n in notes:
            pinned_str = "[PINNED] " if n['pinned'] else ""
            item_text = f"{pinned_str}{n['title']}  [{n['category']}]\n{n['content'][:80]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, n['id'])
            self.lst_notes.addItem(item)

    # Chat History Methods
    def _load_chat_sessions(self):
        self.lst_sessions.clear()
        sessions = self.db.get_all_chat_sessions()
        if not sessions:
            # Create a default session if none exists
            new_s = self.db.create_chat_session("Quick Chat")
            sessions = [new_s]

        for s in sessions:
            dt = s['created_at'][:10]
            item_text = f"{s['title']}\n<span style='font-size:10px; color:#9ca3af;'>{dt} • {s['model']}</span>"
            lbl = QLabel(item_text)
            lbl.setStyleSheet("color: #ffffff; font-size: 12px;")
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, s['id'])
            item.setSizeHint(lbl.sizeHint())
            self.lst_sessions.addItem(item)
            self.lst_sessions.setItemWidget(item, lbl)

        # Select first session by default
        if self.lst_sessions.count() > 0:
            first_item = self.lst_sessions.item(0)
            self.lst_sessions.setCurrentItem(first_item)
            self._on_session_selected(first_item)

    def _on_session_selected(self, item):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_session_id = session_id
        self._load_session_thread(session_id)

    def _load_session_thread(self, session_id):
        self.lst_dash_messages.clear()
        messages = self.db.get_chat_messages(session_id)
        sessions = self.db.get_all_chat_sessions()
        curr_session = next((s for s in sessions if s['id'] == session_id), None)

        if curr_session:
            self.lbl_chat_title.setText(curr_session['title'])
        else:
            self.lbl_chat_title.setText("Chat Session")

        if not messages:
            self._append_dash_bubble("assistant", "Empty conversation. Ask Okum a question below!")
        else:
            for msg in messages:
                self._append_dash_bubble(msg['sender'], msg['content'])

    def _append_dash_bubble(self, sender, text):
        is_user = sender == 'user'
        align_html = "right" if is_user else "left"
        name_tag = "You" if is_user else "Okum"
        name_color = "#a5b4fc" if is_user else "#38bdf8"

        formatted_body = format_chat_text(text)

        html = f"""
        <div style="text-align: {align_html}; margin-bottom: 4px;">
            <div style="font-size: 11px; font-weight: bold; color: {name_color}; margin-bottom: 3px;">{name_tag}</div>
            <div style="text-align: left; background: transparent; color: #f3f4f6; font-size: 13px; word-wrap: break-word; white-space: normal;">
                {formatted_body}
            </div>
        </div>
        """

        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setFixedWidth(530)
        lbl.setContentsMargins(0, 0, 0, 4)

        # Accurate height calculation using QTextDocument with font metrics to prevent vertical text cut-off
        doc = QTextDocument()
        doc.setDefaultFont(QFont('Inter', 10))
        doc.setDocumentMargin(4)
        doc.setHtml(html)
        doc.setTextWidth(530)
        calc_height = int(doc.documentLayout().documentSize().height()) + 24

        item = QListWidgetItem()
        item.setSizeHint(QSize(530, max(calc_height, 40)))
        self.lst_dash_messages.addItem(item)
        self.lst_dash_messages.setItemWidget(item, lbl)
        self.lst_dash_messages.scrollToBottom()

    def _create_new_chat_session(self):
        new_session = self.db.create_chat_session("New Chat")
        self._load_chat_sessions()

    def _clear_all_chats(self):
        reply = QMessageBox.question(self, "Clear All Chats", "Are you sure you want to delete all chat history?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_all_chats()
            self._load_chat_sessions()

    def _on_dash_ai_changed(self, index):
        provider = self.combo_dash_ai.currentData() or "local"
        self.db.set_setting('ai_provider', provider)
        if provider == "groq":
            self.txt_dash_prompt.setPlaceholderText("Continue asking Okum (Groq llama-3.3-70b)...")
        else:
            self.txt_dash_prompt.setPlaceholderText("Continue asking Okum (qwen2.5:1.5b)...")

    def _send_dash_question(self):
        prompt = self.txt_dash_prompt.text().strip()
        if not prompt or not self.selected_session_id:
            return

        self.txt_dash_prompt.clear()
        self._append_dash_bubble("user", prompt)
        self.db.save_chat_message(self.selected_session_id, "user", prompt)

        provider = self.combo_dash_ai.currentData() or "local"
        if provider == "groq":
            self.lbl_dash_thinking.setText("Querying Groq Cloud (llama-3.3-70b)...")
        else:
            self.lbl_dash_thinking.setText("Okum is thinking locally (qwen2.5:1.5b)...")
        self.lbl_dash_thinking.show()
        self.txt_dash_prompt.setEnabled(False)
        self.btn_dash_send.setEnabled(False)

        self.dash_worker = AIQueryWorker(prompt, self.selected_session_id, provider=provider)
        self.dash_worker.response_ready.connect(self._on_dash_query_success)
        self.dash_worker.error_occurred.connect(self._on_dash_query_error)
        self.dash_worker.start()

    def _on_dash_query_success(self, response_text, session_id, prompt):
        self.lbl_dash_thinking.hide()
        self.txt_dash_prompt.setEnabled(True)
        self.btn_dash_send.setEnabled(True)
        self.txt_dash_prompt.setFocus()

        self.db.save_chat_message(session_id, "assistant", response_text)
        self._append_dash_bubble("assistant", response_text)

    def _on_dash_query_error(self, err_msg, session_id):
        self.lbl_dash_thinking.hide()
        self.txt_dash_prompt.setEnabled(True)
        self.btn_dash_send.setEnabled(True)

        self._append_dash_bubble("assistant", f"Warning: {err_msg}")

    def _on_note_double_clicked(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        self.open_notepad_callback(note_id)

    def _on_create_note(self):
        self.hide()
        self.open_notepad_callback()

    def _toggle_focus_timer(self):
        if self._focus_running:
            self._focus_timer.stop()
            self._focus_running = False
            self.btn_timer_start.setText("Resume Focus")
        else:
            self._focus_timer.start(1000)
            self._focus_running = True
            self.btn_timer_start.setText("Pause")

    def _tick_focus_timer(self):
        self._focus_seconds -= 1
        m, s = divmod(self._focus_seconds, 60)
        self.lbl_timer.setText(f"{m:02d}:{s:02d}")
        if self._focus_seconds <= 0:
            self._focus_timer.stop()
            self._focus_running = False
            self.btn_timer_start.setText("Start Focus")

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Backup", "okum_notes.json", "JSON Files (*.json)")
        if path:
            import json
            notes = self.db.get_all_notes()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2)
            QMessageBox.information(self, "Export Success", f"Exported {len(notes)} notes to {path}")

    def _open_md_folder(self):
        import os
        os.system('xdg-open ~/Documents/OkumNotes &')

