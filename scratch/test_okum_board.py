import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import Database
from ui.quick_window import QuickWindow
from ui.board_window import OkumBoardManager

def test_board_tooling():
    app = QApplication(sys.argv)
    
    # Load QSS Theme
    qss_path = os.path.join(os.path.dirname(__file__), '..', 'styles', 'theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # 1. Test OkumBoardManager singleton
    manager = OkumBoardManager.get_instance()
    assert manager is not None, "Manager failed to initialize!"
    print("[1] OkumBoardManager initialized successfully.")

    # 2. Test show_board & canvas setup
    manager.show_board()
    assert manager.is_active is True
    assert manager.canvas.isVisible() is True
    assert manager.toolbar.isVisible() is True
    print(f"[2] Board activated. Canvas geometry: {manager.canvas.geometry().width()}x{manager.canvas.geometry().height()}")

    # 3. Test Drawing Marker Strokes
    canvas = manager.canvas
    canvas.set_tool('marker')
    canvas.set_color('#6366f1')
    canvas.set_thickness(6)

    # Draw several curvy lines across screen
    canvas._draw_stroke(QPoint(100, 100), QPoint(300, 250))
    canvas._draw_stroke(QPoint(300, 250), QPoint(500, 150))
    canvas._draw_stroke(QPoint(500, 150), QPoint(700, 350))
    print("[3] Marker strokes drawn on canvas pixmap.")

    # 4. Test Contact Eraser
    canvas.set_tool('eraser')
    canvas._draw_stroke(QPoint(290, 240), QPoint(310, 260))
    print("[4] Contact eraser applied over intersection.")

    # 5. Test Color & Thickness Cycling
    toolbar = manager.toolbar
    toolbar._cycle_color()
    print(f"[5] Cycled color to: {canvas.marker_color.name()}")
    toolbar._cycle_thickness()
    print(f"[6] Cycled thickness to: {canvas.marker_thickness}px")

    # 6. Test Screenshot Capture
    screenshot_dir = os.path.expanduser('~/Pictures/OkumScreenshots')
    initial_count = len(os.listdir(screenshot_dir)) if os.path.exists(screenshot_dir) else 0
    manager._capture_screenshot_proc()
    new_count = len(os.listdir(screenshot_dir)) if os.path.exists(screenshot_dir) else 0
    print(f"[7] Screenshot capture tested. Files in ~/Pictures/OkumScreenshots: {new_count}")
    assert new_count >= initial_count + 1, "Screenshot file not saved!"

    # 7. Capture visual screenshot of the floating toolbar and annotations
    test_shots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(test_shots_dir, exist_ok=True)
    app.processEvents()
    
    toolbar.grab().save(os.path.join(test_shots_dir, "okum_board_toolbar.png"))
    print("[8] Saved screenshot: okum_board_toolbar.png")

    # 8. Test QuickWindow header button integration
    db = Database()
    qw = QuickWindow(db, lambda: None)
    qw.show()
    assert hasattr(qw, 'btn_tab_board'), "QuickWindow missing btn_tab_board!"
    print("[9] QuickWindow has btn_tab_board in header.")

    qw.grab().save(os.path.join(test_shots_dir, "quick_window_4tabs.png"))
    print("[10] Saved screenshot: quick_window_4tabs.png")

    # 9. Clean up
    manager.close_board()
    qw.close()
    print("ALL OKUM BOARD TOOLING TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_board_tooling()
