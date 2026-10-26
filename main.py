#!/usr/bin/env python3
import sys
import os
import random

# Auto-switch to virtual environment python if not already running in it
venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv')
venv_python = os.path.join(venv_dir, 'bin', 'python3')
if os.path.isdir(venv_dir) and sys.prefix != venv_dir and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

# Ensure package imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QRadialGradient
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtMultimedia import QMediaPlayer

from db.database import Database
from ui.orb_widget import FloatingOrb
from ui.quick_window import QuickWindow
from ui.dashboard_window import DashboardWindow
from ui.board_window import OkumBoardManager
from ui.floating_music_window import FloatingMusicWindow

def create_tray_icon_pixmap():
    icon_path = os.path.join(os.path.dirname(__file__), 'styles', 'okum.png')
    if os.path.exists(icon_path):
        return QPixmap(icon_path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(245, 158, 11))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.setBrush(QColor(254, 240, 138))
    painter.drawEllipse(10, 10, 12, 12)
    painter.end()
    return pixmap

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("okum")
    app.setDesktopFileName("okum")
    app.setOrganizationName("okum")
    app.setQuitOnLastWindowClosed(False)

    icon_path = os.path.join(os.path.dirname(__file__), 'styles', 'okum.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Load QSS Theme
    qss_path = os.path.join(os.path.dirname(__file__), 'styles', 'theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # Initialize Database
    db = Database()

    dashboard = None
    quick_window = None
    spider = None

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

        if spider:
            quick_window.position_near_orb(spider.pos())

        quick_window.show()
        quick_window.raise_()
        quick_window.activateWindow()

    def toggle_quick_window():
        nonlocal quick_window
        if quick_window and quick_window.isVisible():
            quick_window.hide()
        else:
            open_quick_window()

    def open_music_player():
        open_quick_window(tab_index=2)

    def toggle_mini_music_player():
        FloatingMusicWindow.get_instance(open_music_player).toggle_player()

    def toggle_board():
        OkumBoardManager.get_instance().toggle_board()

    def check_okum_active():
        # Check if any Okum window is currently open / visible
        if quick_window and quick_window.isVisible():
            return True
        if dashboard and dashboard.isVisible():
            return True
        if FloatingMusicWindow._instance and FloatingMusicWindow._instance.isVisible():
            return True
        board_mgr = OkumBoardManager.get_instance()
        if board_mgr.canvas and board_mgr.canvas.isVisible():
            return True
        # Check if music is currently playing
        from services.music_service import MusicService
        from PyQt6.QtMultimedia import QMediaPlayer
        ms = MusicService.get_instance()
        if ms and hasattr(ms, 'player') and ms.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return True
        return False

    # Create Floating Living Orb Mascot Widget
    orb = FloatingOrb(
        toggle_callback=toggle_quick_window,
        open_music_callback=open_music_player,
        toggle_board_callback=toggle_board,
        activity_callback=check_okum_active,
        toggle_mini_music_callback=toggle_mini_music_player,
        exit_callback=lambda: exit_okum()
    )
    orb.position_initial()
    orb.show()
    spider = orb  # For backward-compatible variable references

    # Initialize Voice Assistant & Neural Female TTS
    from services.tts_service import TTSService
    from services.voice_service import VoiceService
    from services.music_service import MusicService
    from services.ai_service import AIQueryWorker
    import subprocess
    from datetime import datetime

    tts = TTSService.get_instance()
    music_svc = MusicService.get_instance(db)
    voice = VoiceService.get_instance(tts_service=tts, music_service=music_svc)

    # Sync music state to orb for rhythm pulse & satellite reveal
    def on_music_state(playing):
        orb.set_music_playing(playing)

    music_svc.state_changed.connect(on_music_state)
    orb.set_music_playing(music_svc.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

    def on_tts_state(state):
        if state == "speaking":
            orb.set_voice_state("SPEAKING")
        elif state == "idle" and orb.voice_state == "SPEAKING":
            orb.set_voice_state("IDLE")

    tts.state_changed.connect(on_tts_state)

    # Wire Voice Command Handlers
    def handle_minimize():
        # User specified reaction: "minimising tabs"
        tts.speak("Minimising tabs.")
        try:
            subprocess.run(['wmctrl', '-k', 'on'], check=False)
        except Exception as e:
            print(f"[VoiceAssistant] Error minimizing tabs: {e}")

    def handle_mini_player():
        tts.speak("Mini player.")
        toggle_mini_music_player()

    def handle_play_music():
        from services.music_service import MusicService
        from PyQt6.QtMultimedia import QMediaPlayer
        ms = MusicService.get_instance(db)
        if ms:
            if ms.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                ms.player.play()
            elif not ms.current_track:
                all_tracks = db.search_music_tracks(limit=1000)
                if all_tracks:
                    ms.play_track(all_tracks[0], playlist=all_tracks)
                else:
                    ms.toggle_play_pause()
            else:
                ms.player.play()
        reaction = random.choice(["Got it.", "Yes sir."])
        tts.speak(reaction)

    def handle_pause_music():
        from services.music_service import MusicService
        ms = MusicService.get_instance(db)
        if ms:
            ms.pause()
        tts.speak("Pausing music.")

    def handle_prev_track():
        from services.music_service import MusicService
        ms = MusicService.get_instance(db)
        if ms:
            ms.prev_track()
        tts.speak("Playing previous track.")

    def handle_next_track():
        from services.music_service import MusicService
        ms = MusicService.get_instance(db)
        if ms:
            ms.next_track()
        tts.speak("Playing next track.")

    def handle_shuffle_on():
        from services.music_service import MusicService
        ms = MusicService.get_instance(db)
        if ms:
            if not ms.current_playlist:
                all_tracks = db.search_music_tracks(limit=1000)
                if all_tracks:
                    ms.current_playlist = all_tracks
            ms.set_shuffle(True)
        tts.speak("Shuffle on.")

    def handle_shuffle_off():
        from services.music_service import MusicService
        ms = MusicService.get_instance(db)
        if ms:
            ms.set_shuffle(False)
        tts.speak("Shuffle off.")

    def handle_time():
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        tts.speak(f"The time is {time_str}.")

    def handle_date():
        now = datetime.now()
        day = now.day
        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        date_str = now.strftime(f"%A, %B {day}{suffix}, %Y")
        tts.speak(f"Today is {date_str}.")

    def handle_wake_word():
        spider.set_voice_state("LISTENING")
        # Okum says "Cool" on wake word
        tts.speak("Cool", on_finish=lambda: spider.set_voice_state("LISTENING"))
        # Fallback safety reset if query is not captured or cancelled
        QTimer.singleShot(7500, lambda: spider.set_voice_state("IDLE") if spider.voice_state == "LISTENING" else None)

    current_ai_worker = None

    def handle_chat_query(query_text):
        nonlocal current_ai_worker
        print(f"[VoiceAssistant] User query: {query_text}")
        spider.set_voice_state("THINKING")

        system_prompt = (
            "You are Okum, an intelligent, exciting, and friendly desktop personal assistant for mphatic. "
            "The user is speaking to you via voice. Respond with a short, balanced answer (1 to 3 sentences maximum): "
            "concise, clear, informative, not too long, and not too shallow. "
            "Never use markdown formatting, bullet points, asterisks, citations, or URLs. Speak naturally."
        )

        def on_ai_response(reply, session_id, prompt):
            nonlocal current_ai_worker
            current_ai_worker = None
            clean_reply = reply.replace('*', '').replace('#', '').strip()
            spider.set_voice_state("SPEAKING")
            tts.speak(clean_reply, on_finish=lambda: spider.set_voice_state("IDLE"))

        def on_ai_error(err_msg, session_id):
            nonlocal current_ai_worker
            current_ai_worker = None
            spider.set_voice_state("IDLE")
            tts.speak("I'm sorry, I ran into an issue answering that.")

        current_ai_worker = AIQueryWorker(
            prompt=query_text,
            session_id="voice_chat",
            provider="groq",
            system_prompt=system_prompt
        )
        current_ai_worker.response_ready.connect(on_ai_response)
        current_ai_worker.error_occurred.connect(on_ai_error)
        current_ai_worker.start()

    def handle_voice_status_changed(status):
        if status == "idle":
            if spider.voice_state == "LISTENING":
                spider.set_voice_state("IDLE")
        elif status == "capturing":
            spider.set_voice_state("LISTENING")
        elif status == "muted":
            spider.set_voice_state("IDLE")

    # Connect signals from listener thread
    voice.listener_thread.sig_command_minimize.connect(handle_minimize)
    voice.listener_thread.sig_command_mini_player.connect(handle_mini_player)
    voice.listener_thread.sig_command_play_music.connect(handle_play_music)
    voice.listener_thread.sig_command_pause_music.connect(handle_pause_music)
    voice.listener_thread.sig_command_prev_track.connect(handle_prev_track)
    voice.listener_thread.sig_command_next_track.connect(handle_next_track)
    voice.listener_thread.sig_command_shuffle_on.connect(handle_shuffle_on)
    voice.listener_thread.sig_command_shuffle_off.connect(handle_shuffle_off)
    voice.listener_thread.sig_command_time.connect(handle_time)
    voice.listener_thread.sig_command_date.connect(handle_date)
    voice.listener_thread.sig_wake_word.connect(handle_wake_word)
    voice.listener_thread.sig_chat_query.connect(handle_chat_query)
    voice.listener_thread.sig_status_changed.connect(handle_voice_status_changed)

    # Start low-footprint voice listener
    voice.start()

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
    SVG_MINI_PLAYER = '<rect x="2" y="4" width="20" height="16" rx="2"/><rect x="12" y="10" width="7" height="6" rx="1"/>'
    SVG_BOARD = '<path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/><path d="M14 6l4 4"/><path d="M4 20h16"/>'
    SVG_DASH = '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'
    SVG_MIC = '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>'
    SVG_EXIT = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'

    tray_menu = QMenu()

    # Prominent Voice / Microphone Toggle (default is ON, dead-simple click to mute)
    act_voice = QAction(create_svg_icon(SVG_MIC, stroke_color="#06b6d4"), "Microphone: Listening (Click to Turn OFF)", tray_menu)
    def toggle_voice_mute():
        muted = voice.toggle_mute()
        if muted:
            act_voice.setText("Microphone: OFF / Muted (Click to Turn ON)")
            act_voice.setIcon(create_svg_icon(SVG_MIC, stroke_color="#ef4444"))
            spider.set_voice_state("IDLE")
            spider.setToolTip("Okum — Microphone is OFF / Muted")
        else:
            act_voice.setText("Microphone: Listening (Click to Turn OFF)")
            act_voice.setIcon(create_svg_icon(SVG_MIC, stroke_color="#06b6d4"))
            spider.setToolTip("Okum Spider — Click to open Notes & AI | Drag to move")
    act_voice.triggered.connect(toggle_voice_mute)

    act_note = QAction(create_svg_icon(SVG_BOLT, stroke_color="#a5b4fc"), "Quick Assistant (Notes & Ask AI)", tray_menu)
    act_note.triggered.connect(lambda: open_quick_window())

    act_music = QAction(create_svg_icon(SVG_MUSIC, stroke_color="#a5b4fc"), "Quick Play (Music Player)", tray_menu)
    act_music.triggered.connect(open_music_player)

    act_mini_music = QAction(create_svg_icon(SVG_MINI_PLAYER, stroke_color="#a5b4fc"), "Floating Mini Player", tray_menu)
    act_mini_music.triggered.connect(toggle_mini_music_player)

    act_board = QAction(create_svg_icon(SVG_BOARD, stroke_color="#a5b4fc"), "Okum Board (Screen Annotations)", tray_menu)
    act_board.triggered.connect(toggle_board)

    act_dash = QAction(create_svg_icon(SVG_DASH, stroke_color="#a5b4fc"), "Open Dashboard", tray_menu)
    act_dash.triggered.connect(open_dashboard)

    # Clean up resources and guarantee hard exit so NO stray processes remain
    def cleanup():
        try:
            voice.stop()
        except Exception:
            pass
        try:
            tts.stop()
        except Exception:
            pass
        try:
            if quick_window and quick_window.music_service:
                quick_window.music_service.stop()
        except Exception:
            pass
        try:
            FloatingMusicWindow.get_instance().hide_player()
        except Exception:
            pass
        try:
            OkumBoardManager.get_instance().close_board()
        except Exception:
            pass
        try:
            if spider:
                spider.cleanup()
        except Exception:
            pass

    def exit_okum():
        try:
            cleanup()
        except Exception as e:
            print(f"[Okum] Cleanup error: {e}")
        finally:
            try:
                tray_icon.hide()
            except Exception:
                pass
            app.quit()
            import os
            os._exit(0)

    act_quit = QAction(create_svg_icon(SVG_EXIT, stroke_color="#f87171"), "Exit Okum", tray_menu)
    act_quit.triggered.connect(exit_okum)

    tray_menu.addAction(act_voice)
    tray_menu.addSeparator()
    tray_menu.addAction(act_note)
    tray_menu.addAction(act_music)
    tray_menu.addAction(act_mini_music)
    tray_menu.addAction(act_board)
    tray_menu.addAction(act_dash)
    tray_menu.addSeparator()
    tray_menu.addAction(act_quit)

    app.aboutToQuit.connect(cleanup)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.activated.connect(lambda reason: toggle_quick_window() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray_icon.show()

    print("Okum Native Linux Desktop Assistant is running!")
    print("- AI Engine: Groq Cloud AI active")
    print("- Voice Engine: Offline Vosk STT + Neural Female Voice TTS active")
    print("- Mascot: Living Floating Orb (Solar Ember) active with 10s roam & bottom-left dock")
    print("- Music Engine: Smart multi-library & background watcher active")
    print("- Storage: SQLite & Markdown in ~/Documents/OkumNotes/")

    # Single visible source of truth: open quick window on launch so user knows Okum is active
    open_quick_window()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
