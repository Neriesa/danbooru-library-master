# -*- coding: utf-8 -*-

import sqlite3
import threading
import time
from pathlib import Path


from .constants import DEFAULT_IGNORED_TAGS


POST_COLUMNS = {
    "is_fav": "INTEGER DEFAULT 1", "fav_seen": "INTEGER DEFAULT 0", "file_size": "INTEGER",
    "width": "INTEGER", "height": "INTEGER", "artist": "TEXT", "character": "TEXT",
    "copyright": "TEXT", "deleted": "INTEGER DEFAULT 0", "tags_general": "TEXT",
}

_POST_META_SET = ("file_size=excluded.file_size, width=excluded.width, height=excluded.height, "
                  "artist=excluded.artist, character=excluded.character, copyright=excluded.copyright, "
                  "deleted=excluded.deleted, tags_general=excluded.tags_general")

FAV_UPSERT = f"""
INSERT INTO posts (post_id, md5, rating, file_ext, url, verify, status, note, is_fav, fav_seen,
                   file_size, width, height, artist, character, copyright, deleted, tags_general)
VALUES (:post_id, :md5, :rating, :file_ext, :url, :verify, :status, :note, 1, 1,
        :file_size, :width, :height, :artist, :character, :copyright, :deleted, :tags_general)
ON CONFLICT(post_id) DO UPDATE SET
    md5=excluded.md5, rating=excluded.rating, file_ext=excluded.file_ext, url=excluded.url,
    verify=excluded.verify, is_fav=1, fav_seen=1, {_POST_META_SET},
    status = CASE WHEN posts.status = 'site_only' THEN excluded.status
                  WHEN posts.status IN ('unavailable','skipped') AND excluded.status = 'pending' THEN 'pending'
                  ELSE posts.status END,
    note = CASE WHEN posts.status IN ('site_only','unavailable','skipped') AND excluded.status = 'pending'
                THEN NULL ELSE posts.note END
"""

SITE_UPSERT = f"""
INSERT INTO posts (post_id, md5, rating, file_ext, url, verify, status, note, is_fav, fav_seen,
                   file_size, width, height, artist, character, copyright, deleted, tags_general)
VALUES (:post_id, :md5, :rating, :file_ext, :url, :verify, 'site_only', NULL, 0, 0,
        :file_size, :width, :height, :artist, :character, :copyright, :deleted, :tags_general)
ON CONFLICT(post_id) DO UPDATE SET
    md5=excluded.md5, rating=excluded.rating, file_ext=excluded.file_ext, url=excluded.url,
    verify=excluded.verify, {_POST_META_SET}
"""


class LibraryDB:
    def __init__(self, db_path: Path):
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        self._init()

    def _ensure_columns(self, table, cols):
        have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in cols.items():
            if name not in have:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    def _init(self):
        with self.lock:
            c = self.conn
            # Таблица files совместима с v5/v6.
            c.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    filepath TEXT PRIMARY KEY, filename TEXT, filesize INTEGER, mtime REAL,
                    md5 TEXT, phash TEXT, danbooru_id INTEGER, rating TEXT, status TEXT
                )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_files_md5 ON files(md5)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_files_dbid ON files(danbooru_id)")
            c.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    post_id INTEGER PRIMARY KEY, md5 TEXT, rating TEXT, file_ext TEXT,
                    url TEXT, verify INTEGER DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending', note TEXT
                )""")
            self._ensure_columns("posts", POST_COLUMNS)  # миграция с v6
            c.execute("CREATE INDEX IF NOT EXISTS idx_posts_md5 ON posts(md5)")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("""
                CREATE TABLE IF NOT EXISTS site_match (
                    md5 TEXT PRIMARY KEY, state TEXT NOT NULL, post_id INTEGER, note TEXT, checked_at REAL
                )""")
            self._ensure_columns("site_match", {"keep": "INTEGER DEFAULT 0"})
            c.execute("DELETE FROM site_match WHERE state='variant'")  # устаревшая категория v7/v8
            c.execute("CREATE TABLE IF NOT EXISTS tag_prefs (tag TEXT PRIMARY KEY, action TEXT NOT NULL)")
            c.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, src TEXT, dst TEXT,
                    post_id INTEGER, undone INTEGER DEFAULT 0
                )""")
            c.commit()

    # ---- files ----
    def load_files(self) -> dict:
        with self.lock:
            rows = self.conn.execute(
                "SELECT filepath, filesize, mtime, md5, phash, danbooru_id, status FROM files").fetchall()
        return {r["filepath"]: dict(r) for r in rows}

    def upsert_many(self, rows):
        """rows: (filepath, filename, size, mtime, md5, phash, danbooru_id, rating, status)"""
        with self.lock:
            self.conn.executemany("""
                INSERT INTO files (filepath, filename, filesize, mtime, md5, phash, danbooru_id, rating, status)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(filepath) DO UPDATE SET
                    filename=excluded.filename, filesize=excluded.filesize, mtime=excluded.mtime,
                    md5=excluded.md5, phash=excluded.phash, danbooru_id=excluded.danbooru_id,
                    rating=excluded.rating, status=excluded.status
            """, rows)
            self.conn.commit()

    def delete_files(self, paths):
        paths = list(paths)
        with self.lock:
            for i in range(0, len(paths), 500):
                chunk = paths[i:i + 500]
                self.conn.execute(
                    f"DELETE FROM files WHERE filepath IN ({','.join('?' * len(chunk))})", chunk)
            self.conn.commit()

    def rename_path(self, old: str, new: str):
        with self.lock:
            self.conn.execute("DELETE FROM files WHERE filepath=?", (new,))
            self.conn.execute("UPDATE files SET filepath=?, filename=? WHERE filepath=?",
                              (new, Path(new).name, old))
            self.conn.commit()

    def set_files_found(self, md5, post_id, rating):
        with self.lock:
            self.conn.execute("UPDATE files SET status='found', danbooru_id=?, rating=? WHERE md5=?",
                              (post_id, rating, md5))
            self.conn.commit()

    def set_files_not_found(self, md5):
        with self.lock:
            self.conn.execute("UPDATE files SET status='not_found' WHERE md5=? AND status != 'found'", (md5,))
            self.conn.commit()

    def dup_records(self):
        with self.lock:
            rows = self.conn.execute(
                "SELECT filepath, filesize, md5, phash, danbooru_id FROM files "
                "WHERE md5 IS NOT NULL AND md5 != ''").fetchall()
        return [dict(r) for r in rows]

    # ---- posts ----
    def post_by_md5(self, md5):
        with self.lock:
            r = self.conn.execute(
                "SELECT post_id, rating, is_fav, deleted, width, height, file_size FROM posts "
                "WHERE md5=? ORDER BY is_fav DESC LIMIT 1", (md5,)).fetchone()
        return dict(r) if r else None

    def post_by_id(self, post_id):
        with self.lock:
            r = self.conn.execute(
                "SELECT post_id, rating, is_fav, deleted, width, height, file_size FROM posts "
                "WHERE post_id=?", (post_id,)).fetchone()
        return dict(r) if r else None

    def upsert_posts(self, rows, favorites=True) -> int:
        """
        favorites=True  - посты из списка Избранного (is_fav=1).
        favorites=False - посты, найденные поиском по MD5 (is_fav не меняется, новые = 'site_only').
        Возвращает количество ранее не виденных постов.
        """
        if not rows:
            return 0
        with self.lock:
            ids = [r["post_id"] for r in rows]
            existing = {r[0] for r in self.conn.execute(
                f"SELECT post_id FROM posts WHERE post_id IN ({','.join('?' * len(ids))})", ids)}
            self.conn.executemany(FAV_UPSERT if favorites else SITE_UPSERT, rows)
            self.conn.commit()
            return len([i for i in ids if i not in existing])

    def reset_fav_seen(self):
        with self.lock:
            self.conn.execute("UPDATE posts SET fav_seen=0")
            self.conn.commit()

    def finish_full_listing(self) -> int:
        """После полного чтения списка: посты, которых в Избранном больше нет, помечаются is_fav=0."""
        with self.lock:
            cur = self.conn.execute("UPDATE posts SET is_fav=0 WHERE is_fav=1 AND fav_seen=0")
            self.conn.commit()
            return cur.rowcount

    def reconcile_local_posts(self) -> int:
        """Помечает посты Избранного как 'local', если такой файл (по MD5 или ID) уже есть в папке."""
        with self.lock:
            cur = self.conn.execute("""
                UPDATE posts SET status='local'
                WHERE is_fav=1 AND status IN ('pending','failed','unavailable','skipped') AND (
                    (md5 != '' AND md5 IN (SELECT md5 FROM files WHERE md5 IS NOT NULL AND md5 != ''))
                    OR post_id IN (SELECT danbooru_id FROM files WHERE danbooru_id IS NOT NULL)
                )""")
            self.conn.commit()
            return cur.rowcount

    def pending_posts(self, retry_failed: bool):
        with self.lock:
            rows = self.conn.execute(
                "SELECT post_id, md5, rating, file_ext, url, verify FROM posts "
                "WHERE is_fav=1 AND (status='pending' OR (? AND status IN ('failed','unavailable'))) "
                "ORDER BY post_id DESC", (1 if retry_failed else 0,)).fetchall()
        return [dict(r) for r in rows]

    def set_post(self, post_id, status, note=None):
        with self.lock:
            self.conn.execute("UPDATE posts SET status=?, note=? WHERE post_id=?", (status, note, post_id))
            self.conn.commit()

    def mark_post_favorited(self, post_id):
        """После успешного добавления в Favorites на сайте."""
        with self.lock:
            self.conn.execute("""
                UPDATE posts SET is_fav=1, fav_seen=1,
                    status = CASE WHEN status IN ('site_only','failed','unavailable','skipped')
                                  THEN (CASE WHEN md5 != '' AND md5 IN (SELECT md5 FROM files)
                                             THEN 'local' ELSE 'pending' END)
                                  ELSE status END
                WHERE post_id=?""", (post_id,))
            self.conn.commit()

    def mark_post_unfavorited(self, post_id):
        """После успешного снятия отметки Favorites на сайте: пост становится обычным 'site_only'."""
        with self.lock:
            self.conn.execute("UPDATE posts SET is_fav=0, fav_seen=0, status='site_only', note=NULL WHERE post_id=?",
                              (post_id,))
            self.conn.commit()

    def files_for_md5(self, md5):
        with self.lock:
            return [r["filepath"] for r in self.conn.execute("SELECT filepath FROM files WHERE md5=?", (md5,))]

    # ---- теги ----
    def favorite_tag_rows(self):
        with self.lock:
            return [dict(r) for r in self.conn.execute(
                "SELECT artist, character, copyright, tags_general FROM posts WHERE is_fav=1")]

    def ensure_tag_defaults(self):
        """Один раз заносит в скрытые чисто служебные теги (solo, 1girl...). Дальше список ведёте вы."""
        with self.lock:
            if self.get_meta("tag_defaults_seeded") == "1":
                return
            self.conn.executemany("INSERT OR IGNORE INTO tag_prefs (tag, action) VALUES (?, 'ignore')",
                                  [(t,) for t in DEFAULT_IGNORED_TAGS])
            self.conn.commit()
            self.set_meta("tag_defaults_seeded", "1")

    def ignored_tags(self) -> set:
        with self.lock:
            return {r["tag"] for r in self.conn.execute("SELECT tag FROM tag_prefs WHERE action='ignore'")}

    def ignore_tags(self, tags):
        with self.lock:
            self.conn.executemany("INSERT OR REPLACE INTO tag_prefs (tag, action) VALUES (?, 'ignore')",
                                  [(t,) for t in tags])
            self.conn.commit()

    def unignore_tags(self, tags):
        with self.lock:
            self.conn.executemany("DELETE FROM tag_prefs WHERE tag=?", [(t,) for t in tags])
            self.conn.commit()

    def post_stats(self) -> dict:
        with self.lock:
            rows = self.conn.execute(
                "SELECT status, COUNT(*) AS n FROM posts WHERE is_fav=1 GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    # ---- site_match: что мы знаем про каждый уникальный MD5 локальных файлов ----
    def set_match(self, md5, state, post_id=None, note=None):
        with self.lock:
            self.conn.execute("""
                INSERT INTO site_match (md5, state, post_id, note, checked_at) VALUES (?,?,?,?,?)
                ON CONFLICT(md5) DO UPDATE SET state=excluded.state, post_id=excluded.post_id,
                    note=excluded.note, checked_at=excluded.checked_at
            """, (md5, state, post_id, note, time.time()))
            self.conn.commit()

    def set_keep_for_path(self, filepath: str):
        """Пользователь вернул файл из other/ вручную: автоперенос больше не должен его трогать."""
        with self.lock:
            self.conn.execute("UPDATE site_match SET keep=1 WHERE md5 = "
                              "(SELECT md5 FROM files WHERE filepath=?)", (filepath,))
            self.conn.commit()

    def unchecked_md5s(self, recheck_not_found: bool):
        with self.lock:
            rows = self.conn.execute("""
                SELECT DISTINCT md5 FROM files WHERE md5 IS NOT NULL AND md5 != '' AND (
                    md5 NOT IN (SELECT md5 FROM site_match)
                    OR (? AND md5 IN (SELECT md5 FROM site_match WHERE state='not_found')))
            """, (1 if recheck_not_found else 0,)).fetchall()
        return [r["md5"] for r in rows]

    def known_id_unmatched(self):
        """Файлы с известным ID поста (из имени в found/ или из прошлых проверок), ещё без записи в site_match."""
        with self.lock:
            rows = self.conn.execute("""
                SELECT DISTINCT md5, danbooru_id, filepath FROM files
                WHERE danbooru_id IS NOT NULL AND md5 IS NOT NULL AND md5 != ''
                  AND md5 NOT IN (SELECT md5 FROM site_match)""").fetchall()
        return [dict(r) for r in rows]

    def matches_view(self):
        with self.lock:
            rows = self.conn.execute("""
                SELECT f.filepath, f.filesize, f.md5, m.state, m.post_id, m.note, m.keep,
                       p.is_fav, p.deleted, p.artist, p.character, p.copyright,
                       p.width, p.height, p.file_size
                FROM files f
                LEFT JOIN site_match m ON m.md5 = f.md5
                LEFT JOIN posts p ON p.post_id = m.post_id
                WHERE f.md5 IS NOT NULL AND f.md5 != ''""").fetchall()
        return [dict(r) for r in rows]

    # ---- журнал действий ----
    def log_action(self, kind, src=None, dst=None, post_id=None):
        with self.lock:
            self.conn.execute("INSERT INTO actions (ts, kind, src, dst, post_id) VALUES (?,?,?,?,?)",
                              (time.time(), kind, src, dst, post_id))
            self.conn.commit()

    def undo_candidates(self, kind):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, src, dst FROM actions WHERE kind=? AND undone=0 ORDER BY id DESC", (kind,)).fetchall()
        return [dict(r) for r in rows]

    def mark_undone(self, action_id):
        with self.lock:
            self.conn.execute("UPDATE actions SET undone=1 WHERE id=?", (action_id,))
            self.conn.commit()

    # ---- meta ----
    def get_meta(self, key, default=None):
        with self.lock:
            r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_meta(self, key, value):
        with self.lock:
            self.conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            self.conn.commit()

    def close(self):
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
