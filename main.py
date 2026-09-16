#!/usr/bin/env python3
import sys
import os

# Ensure package imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from db.database import Database
from services.ollama_service import preload_model, unload_model
from ui.orb_widget import FloatingOrb
from ui.quick_window import QuickWindow
from ui.dashboard_window import DashboardWindow
from ui.board_window import OkumBoardManager

def create_tray_icon_pixmap():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(99, 102, 241))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawEllipse(12, 12, 8, 8)
    painter.end()
    return pixmap

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Preload Ollama LLM into memory on startup
    preload_model("qwen2.5:1.5b")

    # Load QSS Theme
    qss_path = os.path.join(os.path.dirname(__file__), 'styles', 'theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # Initialize Database
    db = Database()

    dashboard = None
    quick_window = None
    orb = None

    def open_dashboard():
        nonlocal dashboard
        if not dashboard:
            dashboard = DashboardWindow(db, open_quick_window)
        dashboard.show()
        dashboard.raise_()
        dashboard.activateWindow()

    def open_quick_window(note_id=None, tab_index=None):
        nonlocal quick_window
        if not quick_window:
            quick_window = QuickWindow(db, open_dashboard)

        if note_id:
            quick_window.load_note(note_id)
        elif tab_index is None and not quick_window.isVisible():
            quick_window.new_note()

        if tab_index is not None:
            quick_window.tab_group.button(tab_index).setChecked(True)
            quick_window._switch_tab(tab_index)

        if orb:
            quick_window.position_near_orb(orb.pos())

        quick_window.show()
        quick_window.raise_()
        quick_window.activateWindow()

    def toggle_quick_window():
        nonlocal quick_window
        if quick_window and quick_window.isVisible():
            quick_window.hide()
        else:
            open_quick_window()

    # Create Floating Orb Widget
    orb = FloatingOrb(toggle_callback=toggle_quick_window)

    # Screen positioning for floating orb (default to bottom-right corner)
    screen = app.primaryScreen().geometry()
    orb.move(screen.width() - 90, screen.height() - 120)
    orb.show()

    # System Tray Icon
    tray_icon = QSystemTrayIcon(QIcon(create_tray_icon_pixmap()), app)
    tray_icon.setToolTip("Okum — Personal Assistant for mphatic")

    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtCore import QByteArray

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

    SVG_BOLT = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
    SVG_MUSIC = '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'
    SVG_BOARD = '<path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/><path d="M14 6l4 4"/><path d="M4 20h16"/>'
    SVG_DASH = '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'
    SVG_EXIT = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'

    tray_menu = QMenu()
    act_note = QAction(create_svg_icon(SVG_BOLT, stroke_color="#a5b4fc"), "Quick Assistant (Notes & Ask AI)", tray_menu)
    act_note.triggered.connect(lambda: open_quick_window())
    
    act_music = QAction(create_svg_icon(SVG_MUSIC, stroke_color="#a5b4fc"), "Quick Play (Music Player)", tray_menu)
    act_music.triggered.connect(lambda: open_quick_window(tab_index=2))
    
    act_board = QAction(create_svg_icon(SVG_BOARD, stroke_color="#a5b4fc"), "Okum Board (Screen Annotations)", tray_menu)
    act_board.triggered.connect(lambda: OkumBoardManager.get_instance().toggle_board())
    
    act_dash = QAction(create_svg_icon(SVG_DASH, stroke_color="#a5b4fc"), "Open Dashboard", tray_menu)
    act_dash.triggered.connect(open_dashboard)
    
    act_quit = QAction(create_svg_icon(SVG_EXIT, stroke_color="#f87171"), "Exit Okum", tray_menu)
    act_quit.triggered.connect(app.quit)

    tray_menu.addAction(act_note)
    tray_menu.addAction(act_music)
    tray_menu.addAction(act_board)
    tray_menu.addAction(act_dash)
    tray_menu.addSeparator()
    tray_menu.addAction(act_quit)

    # Clean up and unload model and player when app is exiting
    def cleanup():
        unload_model("qwen2.5:1.5b")
        if quick_window and quick_window.music_service:
            quick_window.music_service.stop()
        OkumBoardManager.get_instance().close_board()

    app.aboutToQuit.connect(cleanup)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.activated.connect(lambda reason: toggle_quick_window() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray_icon.show()

    print("Okum Native Linux Desktop Assistant is running!")
    print("- Offline Brain: qwen2.5:1.5b preloading in memory...")
    print("- Floating Orb Widget active on desktop")
    print("- System Tray Icon active")
    print("- SQLite & Markdown storage in ~/Documents/OkumNotes/")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
