import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.expanduser('~/.local/share/okum/okum.db')
MD_DIR = os.path.expanduser('~/Documents/OkumNotes')

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(MD_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS music_tracks (
                    id TEXT PRIMARY KEY,
                    filepath TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album TEXT,
                    duration INTEGER DEFAULT 0,
                    ext TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    play_count INTEGER DEFAULT 0,
                    last_played_at TEXT,
                    updated_at TEXT NOT NULL
                )
            ''')
            try:
                conn.execute('ALTER TABLE music_tracks ADD COLUMN is_favorite INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute('ALTER TABLE music_tracks ADD COLUMN play_count INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute('ALTER TABLE music_tracks ADD COLUMN last_played_at TEXT')
            except sqlite3.OperationalError:
                pass
            conn.execute('UPDATE music_tracks SET play_count = 0 WHERE play_count IS NULL')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_music_title ON music_tracks(title)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_music_artist ON music_tracks(artist)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_music_filename ON music_tracks(filename)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_music_favorite ON music_tracks(is_favorite)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_music_play_count ON music_tracks(play_count DESC, last_played_at DESC)')
            conn.commit()

        # Seed sample note if database is empty
        if not self.get_all_notes():
            now = datetime.now().isoformat()
            self.save_note({
                'id': 'welcome-note-1',
                'title': 'Welcome to Native Okum!',
                'category': 'General',
                'content': 'Hello mphatic!\n\nOkum is your native Linux desktop personal assistant.\n- Click the floating circle anywhere on your screen to take quick notes.\n- Drag the orb anywhere on your desktop.\n- Notes auto-save to SQLite and sync to ~/Documents/OkumNotes/\n- Access Okum anytime from your Linux system tray.',
                'pinned': 1,
                'created_at': now,
                'updated_at': now
            })

    def get_all_notes(self, category=None, search=None):
        query = "SELECT * FROM notes"
        params = []
        conditions = []

        if category and category != 'ALL':
            conditions.append("category = ?")
            params.append(category)

        if search:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY pinned DESC, updated_at DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_note(self, note_id):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_note(self, note_data):
        now = datetime.now().isoformat()
        note_id = note_data.get('id') or f"note_{int(datetime.now().timestamp()*1000)}"
        title = note_data.get('title') or 'Untitled Note'
        category = note_data.get('category') or 'General'
        content = note_data.get('content') or ''
        pinned = 1 if note_data.get('pinned') else 0
        created_at = note_data.get('created_at') or now
        updated_at = now

        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO notes (id, title, category, content, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    content=excluded.content,
                    pinned=excluded.pinned,
                    updated_at=excluded.updated_at
            ''', (note_id, title, category, content, pinned, created_at, updated_at))
            conn.commit()

        # Also write/sync to ~/Documents/OkumNotes/
        self._sync_md_file(title, content)

        return note_id

    def delete_note(self, note_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()

    def _sync_md_file(self, title, content):
        try:
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).rstrip()
            filename = f"{safe_title or 'note'}.md"
            filepath = os.path.join(MD_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n{content}\n")
        except Exception:
            pass

    def get_setting(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def set_setting(self, key, value):
        with self._get_connection() as conn:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
            conn.commit()

    # Chat Sessions & Messages Methods
    def get_or_create_active_session(self, model="qwen2.5:1.5b"):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            
        return self.create_chat_session("Quick Chat", model)

    def create_chat_session(self, title="New Chat", model="qwen2.5:1.5b"):
        now = datetime.now().isoformat()
        session_id = f"chat_{int(datetime.now().timestamp()*1000)}"
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO chat_sessions (id, title, model, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, title, model, now, now))
            conn.commit()
            return {
                'id': session_id,
                'title': title,
                'model': model,
                'created_at': now,
                'updated_at': now
            }

    def get_all_chat_sessions(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_chat_messages(self, session_id):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def save_chat_message(self, session_id, sender, content):
        now = datetime.now().isoformat()
        msg_id = f"msg_{int(datetime.now().timestamp()*1000)}"
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO chat_messages (id, session_id, sender, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (msg_id, session_id, sender, content, now))

            # Auto update session title if it's default and first user message
            if sender == 'user':
                cursor = conn.execute("SELECT COUNT(*) as count FROM chat_messages WHERE session_id = ? AND sender = 'user'", (session_id,))
                count = cursor.fetchone()['count']
                if count <= 1:
                    title_snippet = content[:30].strip().replace('\n', ' ') or "Quick Chat"
                    conn.execute("UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?", (title_snippet, now, session_id))
                else:
                    conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
            else:
                conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))

            conn.commit()
        return msg_id

    def delete_chat_session(self, session_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()

    def clear_all_chats(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM chat_messages")
            conn.execute("DELETE FROM chat_sessions")
            conn.commit()

    # Music Library Methods
    def upsert_music_tracks_batch(self, tracks_data):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.executemany('''
                INSERT INTO music_tracks (id, filepath, filename, title, artist, album, duration, ext, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(filepath) DO UPDATE SET
                    filename=excluded.filename,
                    title=excluded.title,
                    artist=excluded.artist,
                    album=excluded.album,
                    duration=excluded.duration,
                    ext=excluded.ext,
                    updated_at=excluded.updated_at
            ''', [(t['id'], t['filepath'], t['filename'], t['title'], t['artist'], t.get('album', ''), t.get('duration', 0), t.get('ext', ''), now) for t in tracks_data])
            conn.commit()

    def update_track_metadata(self, filepath, title, artist, album, duration):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE music_tracks SET
                    title = ?,
                    artist = ?,
                    album = ?,
                    duration = ?,
                    updated_at = ?
                WHERE filepath = ?
            ''', (title, artist, album, duration, now, filepath))
            conn.commit()

    def search_music_tracks(self, query=None, filter_type=None, limit=50, offset=0):
        where_clauses = []
        params = []
        if query and query.strip():
            where_clauses.append("(title LIKE ? OR artist LIKE ? OR filename LIKE ? OR album LIKE ?)")
            param_q = f"%{query.strip()}%"
            params.extend([param_q, param_q, param_q, param_q])

        if filter_type == 'favorites':
            where_clauses.append("is_favorite = 1")
        elif filter_type == 'downloads':
            where_clauses.append("(filepath LIKE '%/Downloads/%' OR filepath LIKE '%/downloads/%')")
        elif filter_type == 'music':
            where_clauses.append("(filepath LIKE '%/Music/%' OR filepath LIKE '%/music/%')")

        sql = "SELECT * FROM music_tracks"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        if filter_type == 'recent':
            sql += " ORDER BY COALESCE(last_played_at, updated_at) DESC, ROWID DESC"
        else:
            sql += " ORDER BY play_count DESC, last_played_at DESC, updated_at DESC, title COLLATE NOCASE ASC"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_music_tracks_count(self, query=None, filter_type=None):
        where_clauses = []
        params = []
        if query and query.strip():
            where_clauses.append("(title LIKE ? OR artist LIKE ? OR filename LIKE ? OR album LIKE ?)")
            param_q = f"%{query.strip()}%"
            params.extend([param_q, param_q, param_q, param_q])

        if filter_type == 'favorites':
            where_clauses.append("is_favorite = 1")
        elif filter_type == 'downloads':
            where_clauses.append("(filepath LIKE '%/Downloads/%' OR filepath LIKE '%/downloads/%')")
        elif filter_type == 'music':
            where_clauses.append("(filepath LIKE '%/Music/%' OR filepath LIKE '%/music/%')")

        sql = "SELECT COUNT(*) as count FROM music_tracks"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_all_tracks_for_playback(self, query=None, filter_type=None):
        """Returns all matching tracks for true library-wide playback and shuffle."""
        where_clauses = []
        params = []
        if query and query.strip():
            where_clauses.append("(title LIKE ? OR artist LIKE ? OR filename LIKE ? OR album LIKE ?)")
            param_q = f"%{query.strip()}%"
            params.extend([param_q, param_q, param_q, param_q])

        if filter_type == 'favorites':
            where_clauses.append("is_favorite = 1")
        elif filter_type == 'downloads':
            where_clauses.append("(filepath LIKE '%/Downloads/%' OR filepath LIKE '%/downloads/%')")
        elif filter_type == 'music':
            where_clauses.append("(filepath LIKE '%/Music/%' OR filepath LIKE '%/music/%')")

        sql = "SELECT * FROM music_tracks"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        if filter_type == 'recent':
            sql += " ORDER BY COALESCE(last_played_at, updated_at) DESC, ROWID DESC"
        else:
            sql += " ORDER BY play_count DESC, last_played_at DESC, updated_at DESC, title COLLATE NOCASE ASC"

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def record_track_play(self, filepath):
        """Records playback history and increments play count for track."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE music_tracks
                SET play_count = COALESCE(play_count, 0) + 1,
                    last_played_at = ?
                WHERE filepath = ?
            ''', (now, filepath))
            conn.commit()
            cursor = conn.execute("SELECT play_count FROM music_tracks WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            return row['play_count'] if row else 1

    def toggle_track_favorite(self, filepath):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT is_favorite FROM music_tracks WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            new_val = 1
            if row and row['is_favorite']:
                new_val = 0
            conn.execute("UPDATE music_tracks SET is_favorite = ? WHERE filepath = ?", (new_val, filepath))
            conn.commit()
            return bool(new_val)

    def is_track_favorite(self, filepath):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT is_favorite FROM music_tracks WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            return bool(row['is_favorite']) if row and row['is_favorite'] else False

    def get_all_music_filepaths(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT filepath, duration FROM music_tracks")
            return [dict(row) for row in cursor.fetchall()]

    def delete_music_tracks_batch(self, filepaths):
        if not filepaths:
            return
        with self._get_connection() as conn:
            conn.executemany("DELETE FROM music_tracks WHERE filepath = ?", [(fp,) for fp in filepaths])
            conn.commit()

    def delete_music_track(self, filepath):
        if not filepath:
            return
        with self._get_connection() as conn:
            conn.execute("DELETE FROM music_tracks WHERE filepath = ?", (filepath,))
            conn.commit()



