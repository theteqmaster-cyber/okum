import os
import sys

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from db.database import Database
from ui.quick_window import QuickWindow

def test_recent_notes_tab():
    app = QApplication(sys.argv)
    qss_path = os.path.join(os.path.dirname(__file__), '..', 'styles', 'theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    db = Database()
    qw = QuickWindow(db, lambda: None)
    qw.show()

    # 1. Verify category button names
    btn_names = [btn.text() for btn in qw.cat_group.buttons()]
    print("[1] Category button names:", btn_names)
    assert btn_names == ["General", "Ideas", "Tasks", "Recent"], f"Unexpected categories: {btn_names}"

    # 2. Click "Recent" button
    recent_btn = next(btn for btn in qw.cat_group.buttons() if btn.text() == "Recent")
    recent_btn.click()
    assert qw.note_body_stack.currentIndex() == 1, "Expected note_body_stack index 1 for Recent view"
    count = qw.lst_recent_notes.count()
    print(f"[2] Recent notes view active. Items displayed: {count}")
    assert count > 0, "Recent notes list is empty!"

    # 3. Capture screenshot of Recent Notes view
    screenshot_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)
    app.processEvents()
    qw.grab().save(os.path.join(screenshot_dir, "quick_note_recent_view.png"))
    print("[3] Saved screenshot: quick_note_recent_view.png")

    # 4. Test Search filter
    qw.txt_recent_search.setText("vunotho")
    app.processEvents()
    filtered_count = qw.lst_recent_notes.count()
    print(f"[4] Filtered by 'vunotho', items displayed: {filtered_count}")
    assert filtered_count > 0, "No notes found for query 'vunotho'"

    # 5. Click first filtered item to load note
    first_item = qw.lst_recent_notes.item(0)
    note_id = first_item.data(100) # UserRole
    print(f"[5] Clicking note item: {note_id}")
    qw.lst_recent_notes.itemClicked.emit(first_item)
    app.processEvents()

    assert qw.note_body_stack.currentIndex() == 0, "Expected note_body_stack index 0 after selecting a note"
    print(f"[6] Note loaded! Title: {qw.txt_title.text()} | Category: {qw.current_category}")
    assert "vunotho" in qw.txt_title.text().lower()

    # 6. Capture screenshot of loaded note
    app.processEvents()
    qw.grab().save(os.path.join(screenshot_dir, "quick_note_loaded_from_recent.png"))
    print("[7] Saved screenshot: quick_note_loaded_from_recent.png")

    # 7. Test New Note resets to Editor
    qw.btn_new.click()
    assert qw.note_body_stack.currentIndex() == 0
    assert qw.txt_title.text() == ""
    print("[8] New note successfully reset editor view.")

    qw.close()
    print("ALL RECENT NOTES TAB TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_recent_notes_tab()
