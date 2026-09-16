import os
import sys

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap

from db.database import Database
from services.music_service import MusicService, format_time_ms
from ui.quick_window import QuickWindow
from ui.dashboard_window import DashboardWindow

def run_verification():
    app = QApplication(sys.argv)

    # Load QSS Theme
    qss_path = os.path.join(os.path.dirname(__file__), '..', 'styles', 'theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    db = Database()
    print("[1] Database initialized.")
    count = db.get_music_tracks_count()
    print(f"[2] Total music tracks indexed in SQLite: {count}")
    assert count > 0, "No music tracks indexed!"

    # Test Search & Pagination
    results = db.search_music_tracks(query="", limit=50, offset=0)
    print(f"[3] Page 1 returned {len(results)} tracks. First track: {results[0]['title']} by {results[0]['artist']}")
    assert len(results) > 0, "Page 1 returned empty!"

    # Test Filter Search
    filter_res = db.search_music_tracks(query="Gotye", limit=10, offset=0)
    print(f"[4] Search query 'Gotye' returned {len(filter_res)} tracks.")

    # Initialize MusicService
    music_svc = MusicService.get_instance(db)
    print("[5] MusicService instance created.")

    # Test QuickWindow UI
    qw = QuickWindow(db, lambda: None)
    qw.show()
    print("[6] QuickWindow rendered.")

    # Switch to Quick Play tab (Tab 2)
    qw.tab_group.button(2).setChecked(True)
    qw._switch_tab(2)
    print(f"[7] Switched to Quick Play tab. Displayed items in list: {qw.lst_music.count()}")
    assert qw.lst_music.count() > 0, "Music list is empty on UI!"

    # Test Play track
    test_track = results[0]
    music_svc.play_track(test_track)
    print(f"[8] Playing test track: {test_track['title']}")
    assert music_svc.current_track is not None

    # Test Next Track & Shuffle
    music_svc.toggle_shuffle()
    print(f"[9] Shuffle toggled. is_shuffle = {music_svc.is_shuffle}")
    music_svc.cycle_loop_mode()
    print(f"[10] Loop mode cycled. loop_mode = {music_svc.loop_mode}")

    # Switch to Ask Okum tab (Tab 1) and test long message rendering without clipping
    qw.tab_group.button(1).setChecked(True)
    qw._switch_tab(1)
    
    test_markdown_ai = """A tree is a type of plant with a specific structure that includes several main characteristics:
1. It has woody stems or trunks.
2. Branches grow out from the trunk in a tree's canopy.
3. Leaves are often present on branches and may be green for photosynthesis.
4. Some trees have flowers, while others produce fruits or seeds.

Trees play essential roles in ecosystems by providing habitats oxygen production storing carbon dioxide and helping regulate global temperatures."""

    qw._append_message_bubble("user", "what is a tree")
    qw._append_message_bubble("assistant", test_markdown_ai)
    print(f"[11] Rendered test AI chat messages. Total items in chat: {qw.lst_chat.count()}")

    # Capture screenshots of all 3 tabs to verify visual aesthetics
    screenshot_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)

    # Screenshot Tab 1 (AI Mode with fixed text clipping)
    app.processEvents()
    pix_ai = qw.grab()
    pix_ai.save(os.path.join(screenshot_dir, "ai_mode_fixed.png"))
    print("[12] Saved screenshot: ai_mode_fixed.png")

    # Screenshot Tab 2 (Quick Play Mini Player)
    qw.tab_group.button(2).setChecked(True)
    qw._switch_tab(2)
    app.processEvents()
    pix_music = qw.grab()
    pix_music.save(os.path.join(screenshot_dir, "quick_play_tab.png"))
    print("[13] Saved screenshot: quick_play_tab.png")

    # Screenshot Tab 0 (Quick Note)
    qw.tab_group.button(0).setChecked(True)
    qw._switch_tab(0)
    app.processEvents()
    pix_note = qw.grab()
    pix_note.save(os.path.join(screenshot_dir, "quick_note_tab.png"))
    print("[14] Saved screenshot: quick_note_tab.png")

    music_svc.stop()
    qw.close()
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_verification()
