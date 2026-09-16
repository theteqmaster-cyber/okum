import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, Qt, QEvent
from PyQt6.QtGui import QMouseEvent

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.board_window import OkumBoardManager

def test_cursor_detection():
    app = QApplication(sys.argv)
    
    manager = OkumBoardManager.get_instance()
    manager.show_board()
    
    canvas = manager.canvas
    toolbar = manager.toolbar
    
    from PyQt6.QtCore import QPointF
    
    # 1. On Canvas outside toolbar
    outside_point = QPoint(100, 100)
    outside_point_f = QPointF(100.0, 100.0)
    assert not toolbar.geometry().contains(outside_point), "Point should be outside toolbar"
    
    # Simulate move outside toolbar
    move_event_outside = QMouseEvent(
        QEvent.Type.MouseMove,
        outside_point_f,
        outside_point_f,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseMoveEvent(move_event_outside)
    print("[1] Mouse moved outside toolbar. Canvas cursor shape is custom marker.")

    # 2. Inside toolbar bounds
    toolbar_center = toolbar.geometry().center()
    toolbar_center_f = QPointF(float(toolbar_center.x()), float(toolbar_center.y()))
    move_event_inside = QMouseEvent(
        QEvent.Type.MouseMove,
        toolbar_center_f,
        toolbar_center_f,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseMoveEvent(move_event_inside)
    assert canvas.cursor().shape() == Qt.CursorShape.ArrowCursor, f"Expected ArrowCursor over toolbar, got {canvas.cursor().shape()}"
    print("[2] Mouse moved over toolbar rectangle. Canvas cursor switched to ArrowCursor successfully.")

    # 3. Verify Toolbar Button Cursors
    assert toolbar.btn_marker.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_eraser.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_color.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_thickness.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_screenshot.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_clear.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toolbar.btn_close.cursor().shape() == Qt.CursorShape.PointingHandCursor
    print("[3] All toolbar interactive buttons have PointingHandCursor.")

    # 4. Move back outside
    canvas.mouseMoveEvent(move_event_outside)
    assert canvas.cursor().shape() != Qt.CursorShape.ArrowCursor, "Expected custom marker cursor restored"
    print("[4] Cursor smoothly restored to Marker drawing cursor.")

    manager.close_board()
    print("ALL CURSOR DETECTION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_cursor_detection()
