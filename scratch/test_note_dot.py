import os
import sys

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from db.database import Database
from ui.quick_window import QuickWindow

def test_status_dot():
    app = QApplication(sys.argv)
    db = Database()
    qw = QuickWindow(db, lambda: None)
    qw.show()

    # 1. Initially new note should be RED
    qw.new_note()
    style = qw.lbl_save_dot.styleSheet()
    print("[State 1 - Empty Note] Style:", style)
    assert "#ef4444" in style, f"Expected red #ef4444, got {style}"

    # 2. Type text -> should turn YELLOW (unsaved new note)
    qw.txt_title.setText("My Brand New Note")
    qw.txt_content.setText("Writing some interesting ideas here...")
    style = qw.lbl_save_dot.styleSheet()
    print("[State 2 - Unsaved New Note] Style:", style)
    assert "#f59e0b" in style, f"Expected yellow #f59e0b, got {style}"

    # 3. Save note -> should turn GREEN (saved)
    qw.save_note()
    style = qw.lbl_save_dot.styleSheet()
    print("[State 3 - Saved Note] Style:", style)
    assert "#10b981" in style, f"Expected green #10b981, got {style}"

    # 4. Modify note -> should turn PURPLE (unsaved additions / changes)
    qw.txt_content.setText("Writing some interesting ideas here... and here is a new addition!")
    style = qw.lbl_save_dot.styleSheet()
    print("[State 4 - Modified Existing Note] Style:", style)
    assert "#a855f7" in style, f"Expected purple #a855f7, got {style}"

    # 5. Save again -> should turn GREEN
    qw.save_note()
    style = qw.lbl_save_dot.styleSheet()
    print("[State 5 - Re-saved Note] Style:", style)
    assert "#10b981" in style, f"Expected green #10b981, got {style}"

    # 6. Click New Note -> should return to RED
    qw.new_note()
    style = qw.lbl_save_dot.styleSheet()
    print("[State 6 - Reset to Empty] Style:", style)
    assert "#ef4444" in style, f"Expected red #ef4444, got {style}"

    # 7. Take screenshot of Quick Note with the new status dot
    qw.txt_title.setText("vunotho assesment 1 blueprint")
    qw.txt_content.setText("assesemnet of the vunotho blueprint\n\nquestions\nwhat is vunotho\nwhy are we building it")
    qw.save_note() # Green state
    app.processEvents()

    screenshot_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)
    qw.grab().save(os.path.join(screenshot_dir, "quick_note_green_saved.png"))
    print("Saved screenshot: quick_note_green_saved.png")

    qw.txt_content.setText("assesemnet of the vunotho blueprint\n\nquestions\nwhat is vunotho\nwhy are we building it\nhow are we supposed to build it")
    app.processEvents()
    qw.grab().save(os.path.join(screenshot_dir, "quick_note_purple_modified.png"))
    print("Saved screenshot: quick_note_purple_modified.png")

    qw.close()
    print("ALL NOTE STATUS DOT TESTS PASSED!")

if __name__ == '__main__':
    test_status_dot()
