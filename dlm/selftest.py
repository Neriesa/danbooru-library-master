# -*- coding: utf-8 -*-

import shutil
import tkinter as tk
from pathlib import Path

import numpy as np
from . import app_paths
from PIL import Image

from .db import LibraryDB
from .imaging import hash_file, have_cv2
from .i18n import _


def selftest() -> int:
    """Проверка окружения без сети. Результат печатается и пишется в selftest.txt (в папке данных)."""
    import tempfile
    lines, failed = [], [False]

    def check(name, fn):
        try:
            lines.append(f"OK   {name}: {fn() or ''}".rstrip())
        except Exception as e:
            failed[0] = True
            lines.append(f"FAIL {name}: {type(e).__name__}: {e}")

    def t_imports():
        import PIL
        from . import random_viewer  # noqa: F401
        extra = ""
        if have_cv2():
            import cv2
            extra = f", opencv {cv2.__version__}"
        else:
            extra = _(", без OpenCV (облегчённая сборка: видео открываются плеером системы)")
        return f"numpy {np.__version__}, Pillow {PIL.__version__}{extra}"

    def t_hash_and_db():
        tmp = Path(tempfile.mkdtemp())
        db = None
        try:
            p = tmp / "g.png"
            Image.effect_noise((100, 100), 64).convert("RGB").save(p)
            row = hash_file(p, tmp)
            assert len(row[5]) == 16 and row[4], row
            db = LibraryDB(tmp / "t.db")
            db.upsert_many([row])
            assert str(p) in db.load_files()
            return f"pHash {row[5]}"
        finally:
            if db:
                db.close()
            shutil.rmtree(tmp, ignore_errors=True)

    def t_video():
        if not have_cv2():
            return _("пропущено (нет OpenCV)")
        import cv2
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "v.mp4"
            w = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
            if not w.isOpened():
                raise RuntimeError(_("не удалось создать видео (нет кодека mp4v)"))
            for i in range(5):
                w.write(np.full((48, 64, 3), i * 40, np.uint8))
            w.release()
            cap = cv2.VideoCapture(str(p))
            ok, _frame = cap.read()
            cap.release()
            if not ok:
                raise RuntimeError(_("видео создано, но не читается"))
            return _("чтение и запись видео работают")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def t_window():
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return _("окна создаются")

    def t_data_dir():
        d = app_paths.data_base()
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return str(d)

    check(_("библиотеки"), t_imports)
    check(_("хэш и база"), t_hash_and_db)
    check(_("видео"), t_video)
    check(_("окно"), t_window)
    check(_("папка данных"), t_data_dir)
    text = "\n".join(lines) + (_("\nИТОГ: есть ошибки") if failed[0] else _("\nИТОГ: всё в порядке"))
    try:
        (app_paths.data_base() / "selftest.txt").write_text(text, encoding="utf-8")
    except OSError:
        pass
    try:
        print(text)
    except Exception:
        pass
    return 1 if failed[0] else 0
