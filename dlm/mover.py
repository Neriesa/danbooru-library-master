# -*- coding: utf-8 -*-

import shutil
from pathlib import Path


from .constants import MARK_BY_CATEGORY, OTHER_DIR
from .net import Cancelled, STOP
from .db import LibraryDB
from .files import move_file
from .i18n import _


def strip_marks(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for pre in MARK_BY_CATEGORY.values():
            if name.startswith(pre) and len(name) > len(pre):
                name, changed = name[len(pre):], True
    return name


def plan_moves(root: Path, items):
    """Пробный режим: что именно будет перенесено в other/ и под какими именами. Ничего не меняет.
    items: [(путь, категория)]. Возвращает список словарей: src, new_name, category, clash (имя уже занято)."""
    plan = []
    for fp, category in items:
        src = Path(fp)
        if not src.exists() or category not in MARK_BY_CATEGORY:
            continue
        new_name = MARK_BY_CATEGORY[category] + strip_marks(src.name)
        clash = (root / OTHER_DIR / new_name).exists()
        plan.append({"src": str(src), "new_name": new_name, "category": category, "clash": clash})
    return plan


def move_marked(db: LibraryDB, root: Path, items, say, progress):
    """
    Переносит файлы в other/ и добавляет к имени пометку: notFound_ (не найден на сайте)
    или siteDeleted_ (пост удалён с сайта). items: [(путь, категория)]. Обратимо через журнал.
    """
    moved = 0
    for i, (fp, category) in enumerate(items, 1):
        if STOP.is_set():
            raise Cancelled()
        src = Path(fp)
        progress(i, len(items), _("Перенос в {0}/: {1}").format(OTHER_DIR, src.name))
        if not src.exists() or category not in MARK_BY_CATEGORY:
            continue
        new_name = MARK_BY_CATEGORY[category] + strip_marks(src.name)
        try:
            dst = move_file(src, root / OTHER_DIR, new_name)
        except Exception as e:
            say(_("Не удалось перенести {0}: {1}").format(src.name, e), "warn")
            continue
        if dst == src:
            continue
        db.rename_path(str(src), str(dst))
        db.log_action("move_notfound", str(src), str(dst))
        moved += 1
    say(_("Перенесено в {0}/ с пометкой в имени: {1}").format(OTHER_DIR, moved))
    return moved


def undo_moves(db: LibraryDB, kind: str, say):
    restored = skipped = 0
    for a in db.undo_candidates(kind):
        src, dst = Path(a["src"]), Path(a["dst"])
        if not dst.exists():
            db.mark_undone(a["id"])  # файл уже убрали вручную
            skipped += 1
            continue
        if src.exists():
            say(_("Не возвращён (место занято): {0}").format(src), "warn")
            skipped += 1
            continue
        try:
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
        except Exception as e:
            say(_("Не удалось вернуть {0}: {1}").format(dst.name, e), "warn")
            skipped += 1
            continue
        db.rename_path(str(dst), str(src))
        db.mark_undone(a["id"])
        if kind == "move_notfound":
            db.set_keep_for_path(str(src))
        restored += 1
    say(_("Возвращено на прежнее место: {0}, пропущено: {1}").format(restored, skipped))
    return restored, skipped
