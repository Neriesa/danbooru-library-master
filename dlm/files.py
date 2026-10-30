# -*- coding: utf-8 -*-

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from . import app_paths

from .constants import ALL_EXT, GENERAL_DIR, MANAGED_DIRS, OTHER_DIR, SKIP_DIRS
from .config import CONFIG, log
from .i18n import _


def app_data_dir() -> Path:
    """Папка служебных файлов библиотек (в config.json можно переопределить ключом data_dir)."""
    override = CONFIG.get("data_dir")
    return Path(override) if override else app_paths.data_base()


def service_dir(root: Path, create: bool = True) -> Path:
    """Отдельная папка служебных файлов для каждой рабочей папки: <имя>_<хэш пути>."""
    key = hashlib.sha1(str(root.resolve()).lower().encode("utf-8")).hexdigest()[:8]
    name = "".join(c if (c.isalnum() or c in "._-") else "_" for c in root.name)[:40] or "library"
    d = app_data_dir() / "libraries" / f"{name}_{key}"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _move_replace(src: Path, dst: Path):
    try:
        os.replace(src, dst)
    except OSError:                      # другой диск
        shutil.copy2(src, dst)
        src.unlink()


def migrate_service_files(root: Path, svc: Path, say=print):
    """Переносит служебные файлы старых версий из рабочей папки в папку данных программы."""
    names = ["library.db", "library.db-wal", "library.db-shm"]
    old_db, new_db = root / "library.db", svc / "library.db"
    if old_db.exists() and not new_db.exists():
        copied = []
        try:
            for n in names:                                  # база едет вместе с WAL/SHM, сначала копия
                if (root / n).exists():
                    shutil.copy2(root / n, svc / n)
                    copied.append(n)
            check = sqlite3.connect(str(new_db))
            try:
                ok = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            finally:
                check.close()
            if not ok:
                raise RuntimeError(_("проверка целостности скопированной базы не пройдена"))
        except Exception:
            for n in copied:
                (svc / n).unlink(missing_ok=True)
            raise
        for n in copied:
            (root / n).unlink(missing_ok=True)
        say(_("База данных перенесена из рабочей папки в {0}").format(svc))
    elif old_db.exists():
        say(_("В рабочей папке осталась старая library.db (новая уже есть в {0}); её можно удалить вручную.").format(svc))
    for n in ("report.html", "duplicates_report.txt"):
        if (root / n).exists():
            _move_replace(root / n, svc / n)


def rating_folder(rating) -> str:
    """general -> general/, все остальные рейтинги (sensitive, questionable, explicit) -> other/."""
    return GENERAL_DIR if rating == "g" else OTHER_DIR



def iter_library_files(root: Path):
    """Рекурсивно обходит папку, пропуская папку deleted верхнего уровня."""
    for dirpath, dirnames, filenames in os.walk(root):
        if Path(dirpath) == root:
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in ALL_EXT:
                yield p


def managed_post_id(path: Path, root: Path):
    """Файлы, скачанные скриптом (found/<рейтинг>/<id>.ext), содержат ID поста в имени."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    if len(parts) >= 2 and parts[0].lower() in MANAGED_DIRS and path.stem.isdigit():
        return int(path.stem)
    return None


def calculate_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def move_file(src: Path, dst_dir: Path, new_name: str = None) -> Path:
    """Переносит файл, не перезаписывая существующие. new_name позволяет заодно переименовать."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    name = new_name or src.name
    stem, suffix = Path(name).stem, Path(name).suffix
    dst = dst_dir / name
    i = 1
    while dst.exists() and dst != src:
        dst = dst_dir / f"{stem}_{i}{suffix}"
        i += 1
    if dst != src:
        shutil.move(str(src), str(dst))
    return dst


def open_in_system(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        log.warning("Не удалось открыть %s: %s", path, e)
