# -*- coding: utf-8 -*-

from pathlib import Path

from . import app_paths

from .constants import BASE_URL, DEFAULT_IGNORED_TAGS, TRASH_DIR
from .config import get_credentials
from .net import ApiError, STOP, add_favorite, api_request, check_tag_limit
from .db import LibraryDB
from .files import move_file, service_dir
from .actions import remove_favorites_batch
from .i18n import _


class ViewerBridge:
    """
    Даёт окну случайного просмотра то, что знает база программы: ID поста по файлу и безопасное
    «удаление» (снять с Favorites на сайте и перенести файл в deleted/). Папка, которую просматривают,
    должна быть рабочей папкой (или её подпапкой), уже открытой в основной программе.
    """

    def __init__(self):
        self._dbs = {}
        self._roots = {}

    def find_root(self, path: Path):
        folder = path.parent
        if folder not in self._roots:
            found = None
            for parent in [folder, *folder.parents]:
                if (service_dir(parent, create=False) / "library.db").exists():
                    found = parent
                    break
            self._roots[folder] = found
        return self._roots[folder]

    def _db(self, root: Path) -> LibraryDB:
        if root not in self._dbs:
            self._dbs[root] = LibraryDB(service_dir(root, create=False) / "library.db")
        return self._dbs[root]

    def _file_row(self, path: Path):
        root = self.find_root(path)
        if root is None:
            return None, None, None
        db = self._db(root)
        with db.lock:
            row = db.conn.execute("SELECT md5, danbooru_id FROM files WHERE filepath=?", (str(path),)).fetchone()
        return root, db, row

    def post_id_for(self, path: Path):
        root, db, row = self._file_row(path)
        if row is None:
            return None
        if row["danbooru_id"]:
            return row["danbooru_id"]
        with db.lock:
            m = db.conn.execute("SELECT post_id FROM site_match WHERE md5=? AND post_id IS NOT NULL",
                                (row["md5"],)).fetchone()
        return m["post_id"] if m else None

    def removal_info(self, path: Path) -> dict:
        root, db, row = self._file_row(path)
        if root is None:
            return {"root": None}
        md5 = row["md5"] if row else None
        pid = self.post_id_for(path)
        post = db.post_by_id(pid) if pid else None
        copies = len(db.files_for_md5(md5)) if md5 else 1
        return {"root": root, "pid": pid, "md5": md5, "is_fav": bool(post and post["is_fav"]), "copies": max(copies, 1)}

    def remove(self, path: Path) -> dict:
        """Выполняется в фоновом потоке. Возвращает {"ok", "message", "moved": [пути, которые исчезли]}."""
        STOP.clear()
        info = self.removal_info(path)
        root = info.get("root")
        if root is None:
            return {"ok": False, "message": _("Папка не найдена в базе программы."), "moved": []}
        db = self._db(root)
        lines = []
        say = lambda text, level="info": lines.append(text)
        before = [Path(p) for p in db.files_for_md5(info["md5"])] if info.get("md5") else [path]
        if path not in before:
            before.append(path)
        pid, md5 = info.get("pid"), info.get("md5")
        if pid and md5:
            if info["is_fav"] and not (get_credentials()[0] and get_credentials()[1]):
                return {"ok": False, "message": _("Не заданы логин и API-ключ (шаг 1 основной программы)."), "moved": []}
            removed, already, moved, failed = remove_favorites_batch(db, root, [(pid, md5)], say, lambda *a: None)
            ok = failed == 0
            message = (_("Пост #{0} снят с Favorites, файл в {1}/").format(pid, TRASH_DIR) if removed
                       else _("Файл перенесён в {0}/ (пост #{1} не был в Favorites)").format(TRASH_DIR, pid))
        else:
            dst = move_file(path, root / TRASH_DIR)
            db.delete_files([str(path)])
            db.log_action("move_deleted", str(path), str(dst))
            ok, message = True, _("Файл перенесён в {0}/").format(TRASH_DIR)
        gone = [p for p in before if not p.exists()]
        if not ok:
            message = lines[-2] if len(lines) > 1 else (lines[-1] if lines else _("Не удалось"))
        return {"ok": ok, "message": message, "moved": gone}


class BrowseServices:
    """Всё, что окну «Обзор» нужно от программы: вход на сайт, запросы, Favorites, скрытые теги, место для кэша."""

    base_url = BASE_URL

    def __init__(self, db=None, app=None):
        self.db, self.app = db, app
        self.username = get_credentials()[0]
        safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in self.username) or "user"
        self.cache_dir = app_paths.data_base() / "browse" / safe

    def api_json(self, path, params):
        if STOP.is_set() and not (self.app is not None and self.app.busy):
            STOP.clear()                      # «Остановить» на других шагах не должно ломать ленту
        r = api_request("GET", BASE_URL + path, params=params)
        try:
            check_tag_limit(r.status_code, r.text)
            if r.status_code in (401, 403):
                raise ApiError(_("Сайт отклонил запрос (HTTP {0}). Проверьте логин и API-ключ.").format(r.status_code))
            if r.status_code != 200:
                raise ApiError(f"HTTP {r.status_code}: {(r.text or '')[:150]}")
            return r.json(), len(r.content)
        finally:
            r.close()

    def add_favorite(self, post_id):
        return add_favorite(post_id)

    def favorite_ids(self):
        if self.db is None:
            return []
        with self.db.lock:
            return [r[0] for r in self.db.conn.execute("SELECT post_id FROM posts WHERE is_fav=1")]

    def ignored_tags(self):
        if self.db is None:
            return set(DEFAULT_IGNORED_TAGS)
        self.db.ensure_tag_defaults()
        return self.db.ignored_tags()

    def ignore_tags(self, tags):
        if self.db is not None:
            self.db.ignore_tags(tags)
