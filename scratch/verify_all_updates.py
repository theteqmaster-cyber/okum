import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint

def test_music_dirs():
    print("Testing music discovery...")
    from services.music_service import get_music_dirs
    dirs = get_music_dirs()
    print(f"Discovered music dirs: {dirs}")
    assert any("Euro Truck Simulator 2" in d for d in dirs), "ETS2 directory not detected!"
    print("✓ Music discovery passed.")

def test_ai_service():
    print("Testing AI service configuration...")
    from services.ai_service import AIQueryWorker, get_groq_api_key
    key = get_groq_api_key()
    print(f"Groq API Key present: {bool(key)}")
    worker = AIQueryWorker("Hello", "test_session", provider="groq")
    assert worker.provider == "groq"
    print("✓ AI service configured for Groq.")

def test_spider_mascot(app):
    print("Testing Spider mascot initialization & locomotion...")
    from ui.spider_widget import FloatingSpider
    called = []
    spider = FloatingSpider(lambda: called.append(True))
    spider.position_initial()
    assert spider.width() == 88 and spider.height() == 88
    # Test game loop tick
    spider._game_loop()
    print("✓ Spider widget initialized and ticked.")

def test_board_event_routing(app):
    print("Testing Okum Board canvas & embedded toolbar...")
    from ui.board_window import OkumBoardManager
    mgr = OkumBoardManager.get_instance()
    assert mgr.canvas is not None
    assert mgr.toolbar is not None
    assert mgr.toolbar.parent() == mgr.canvas, "Toolbar is not a child of Canvas!"
    print("✓ Okum Board child hierarchy confirmed.")

def test_note_autosave(app):
    print("Testing Note auto-save debouncer...")
    from db.database import Database
    from ui.quick_window import QuickWindow
    db = Database()
    qw = QuickWindow(db, lambda: None)
    qw.new_note()
    qw.txt_title.setText("AutoSave Verification")
    qw.txt_content.setText("Content that should never be lost")
    qw._perform_autosave()
    assert qw.current_note_id is not None
    saved = db.get_note(qw.current_note_id)
    assert saved is not None
    assert saved['title'] == "AutoSave Verification"
    assert saved['content'] == "Content that should never be lost"
    print(f"✓ Note auto-saved to DB with ID: {qw.current_note_id}")

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    test_music_dirs()
    test_ai_service()
    test_spider_mascot(app)
    test_board_event_routing(app)
    test_note_autosave(app)
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    main()
