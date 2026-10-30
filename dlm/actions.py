# -*- coding: utf-8 -*-

import hashlib
import os
from collections import Counter
from pathlib import Path


from .constants import ALL_EXT, GENERAL_DIR, IMAGE_EXT, LEGACY_DIR, OTHER_DIR, TAG_KINDS, TRASH_DIR
from .config import log
from .net import PermissionDenied, ApiError, Cancelled, STOP, add_favorite, api_get, api_json, post_to_row, remove_favorite
from .db import LibraryDB
from .files import move_file, rating_folder
from .dupes import scan_library
from .site import list_favorites
from .i18n import _


def add_favorites_batch(db: LibraryDB, post_ids, say, progress):
    added = already = failed = 0
    for i, pid in enumerate(post_ids, 1):
        if STOP.is_set():
            raise Cancelled()
        progress(i, len(post_ids), _("Добавление в Favorites {0}/{1} (пост {2})").format(i, len(post_ids), pid))
        try:
            res = add_favorite(pid)
        except ApiError as e:
            failed += 1
            say(_("Пост {0}: {1}").format(pid, e), "warn")
            if isinstance(e, PermissionDenied):
                break  # права ключа не изменятся от повторов
            continue
        db.mark_post_favorited(pid)
        db.log_action("fav_add", post_id=pid)
        added += res == "added"
        already += res == "already"
    say(_("Добавлено в Favorites: {0}, уже были: {1}, ошибок: {2}").format(added, already, failed))
    return added, already, failed


def remove_favorites_batch(db: LibraryDB, root: Path, items, say, progress):
    """
    items: [(post_id, md5)]. Снимает отметку Favorites на сайте (если стоит) и переносит ВСЕ локальные файлы
    этого поста в deleted/<id>.<расширение>. Файл переносится только после успешного снятия отметки.
    Передумать: положить файл обратно в папку, при следующей сверке пост будет «не в Favorites».
    """
    removed = already = moved = failed = 0
    for i, (pid, md5) in enumerate(items, 1):
        if STOP.is_set():
            raise Cancelled()
        progress(i, len(items), _("Убираю из Favorites {0}/{1} (пост {2})").format(i, len(items), pid))
        post = db.post_by_id(pid)
        if post and post["is_fav"]:
            try:
                res = remove_favorite(pid)
            except ApiError as e:
                failed += 1
                say(_("Пост {0}: {1}").format(pid, e), "warn")
                if isinstance(e, PermissionDenied):
                    break
                continue
            db.mark_post_unfavorited(pid)
            db.log_action("fav_remove", post_id=pid)
            removed += res == "removed"
            already += res == "already"
        for fp in db.files_for_md5(md5):
            src = Path(fp)
            if not src.exists():
                continue
            try:
                dst = move_file(src, root / TRASH_DIR, f"{pid}{src.suffix}")
            except Exception as e:
                say(_("Не удалось перенести {0}: {1}").format(src.name, e), "warn")
                continue
            db.delete_files([fp])
            db.log_action("move_deleted", str(src), str(dst), pid)
            moved += 1
    say(_("Снято с Favorites: {0}, уже не были: {1}, файлов перенесено в {2}/: {3}, ошибок: {4}").format(removed, already, TRASH_DIR, moved, failed))
    return removed, already, moved, failed


def refresh_tag_data(db: LibraryDB, username: str, limit_posts: int, say, progress):
    """Обновляет теги по последним избранным (новые первыми). Один запрос = 100 постов."""
    tags, page, seen = f"ordfav:{username}", 1, 0
    say(_("Читаю теги последних {0} избранных (примерно {1} запросов)…").format(limit_posts, -(-limit_posts // 100)))
    while seen < limit_posts:
        if STOP.is_set():
            raise Cancelled()
        data = api_json("/posts.json", {"tags": tags, "limit": 100, "page": page})
        if not data and page == 1 and tags.startswith("ordfav:"):
            tags = f"fav:{username}"
            continue
        if not data:
            break
        db.upsert_posts([post_to_row(p) for p in data], favorites=True)
        seen += len(data)
        progress(min(seen, limit_posts), limit_posts, _("Теги: обработано постов {0}").format(seen))
        if len(data) < 100:                  # неполная страница: это конец списка, лишний запрос не нужен
            break
        page += 1
    say(_("Теги обновлены по {0} постам").format(seen))
    return seen


def compute_tag_stats(db: LibraryDB, top_n: int = 10):
    """{вид: {"posts": сколько постов учтено, "top": [(тег, число, процент), ...]}} без скрытых тегов."""
    db.ensure_tag_defaults()
    ignored = db.ignored_tags()
    counters = {k: Counter() for k, _label in TAG_KINDS}
    seen = {k: 0 for k, _label in TAG_KINDS}
    for row in db.favorite_tag_rows():
        for kind, _label in TAG_KINDS:
            raw = row[kind]
            if raw is None:                    # теги этого поста ещё не загружались
                continue
            seen[kind] += 1
            counters[kind].update(t for t in set(raw.split()) if t not in ignored)
    return {k: {"posts": seen[k],
                "top": [(t, n, 100.0 * n / seen[k])
                        for t, n in sorted(counters[k].items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]}
            for k, _label in TAG_KINDS}



def migrate_legacy_found(db: LibraryDB, root: Path, say, progress):
    """
    Переносит файлы старой структуры found/18+ и found/Others в general/ и other/.
    Рейтинг берётся из базы (нужен хотя бы один запуск шага 3 или 5). Без известного рейтинга
    файлы из found/18+ уезжают в other/, остальные остаются на месте.
    """
    legacy = root / LEGACY_DIR
    if not legacy.is_dir():
        say(_("Папки {0}/ нет, переносить нечего.").format(LEGACY_DIR))
        return 0
    files = [p for p in legacy.rglob("*") if p.is_file() and p.suffix.lower() in ALL_EXT]
    moved = left = 0
    for i, p in enumerate(files, 1):
        if STOP.is_set():
            raise Cancelled()
        progress(i, len(files), _("Перенос из {0}/: {1}").format(LEGACY_DIR, p.name))
        rating = None
        if p.stem.isdigit():
            post = db.post_by_id(int(p.stem))
            rating = post["rating"] if post and post.get("rating") else None
        if rating is None and p.relative_to(legacy).parts[0] == "18+":
            rating = "e"
        if rating is None:
            left += 1
            say(_("Рейтинг неизвестен, оставлен на месте: {0}").format(p.name), "warn")
            continue
        try:
            dst = move_file(p, root / rating_folder(rating))
        except Exception as e:
            say(_("Не удалось перенести {0}: {1}").format(p.name, e), "warn")
            continue
        db.rename_path(str(p), str(dst))
        db.log_action("move_legacy", str(p), str(dst))
        moved += 1
    for d in sorted((x for x in legacy.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)):
        try:
            d.rmdir()  # удаляются только пустые папки
        except OSError:
            pass
    try:
        legacy.rmdir()
    except OSError:
        pass
    say(_("Перенесено из {0}/: {1}, оставлено на месте: {2}").format(LEGACY_DIR, moved, left))
    return moved


def download_post(db: LibraryDB, root: Path, row: dict):
    """Скачивает один пост. Возвращает (статус, заметка)."""
    post_id, url = row["post_id"], row["url"]
    ext = row["file_ext"] or "bin"
    folder = root / rating_folder(row["rating"])
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{post_id}.{ext}"
    if target.exists():
        return "downloaded", _("файл уже был на месте")

    tmp = target.with_name(target.name + ".part")
    r = api_get(url, stream=True, timeout=(10, 60))
    try:
        if r.status_code in (403, 404, 410):
            return "unavailable", f"HTTP {r.status_code}"
        r.raise_for_status()
        expected_len = int(r.headers.get("Content-Length") or 0)
        encoded = bool(r.headers.get("Content-Encoding"))
        h = hashlib.md5()
        try:
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(256 * 1024):
                    if STOP.is_set():
                        raise Cancelled()
                    f.write(chunk)
                    h.update(chunk)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    finally:
        r.close()

    digest = h.hexdigest()
    size = tmp.stat().st_size
    if size == 0 or (expected_len and not encoded and size != expected_len):
        tmp.unlink(missing_ok=True)
        return "failed", _("неполная загрузка ({0} из {1} байт)").format(size, expected_len)
    if row["verify"] and row["md5"] and digest != row["md5"]:
        tmp.unlink(missing_ok=True)
        return "failed", _("MD5 скачанного файла не совпал с MD5 поста")

    os.replace(tmp, target)
    st = target.stat()
    phash = "" if target.suffix.lower() in IMAGE_EXT else "-"
    db.upsert_many([(str(target), target.name, st.st_size, st.st_mtime, digest, phash,
                     post_id, row["rating"], "found")])
    return "downloaded", None


def sync_favorites(db: LibraryDB, root: Path, username: str, full: bool, retry_failed: bool, say, progress):
    scan_library(db, root, say, progress)

    for d in (GENERAL_DIR, OTHER_DIR, LEGACY_DIR):
        if (root / d).exists():
            for leftover in (root / d).rglob("*.part"):
                leftover.unlink(missing_ok=True)

    list_favorites(db, username, full, say, progress)
    local = db.reconcile_local_posts()
    say(_("Уже есть в вашей библиотеке (по MD5/ID): {0}").format(local))

    pending = db.pending_posts(retry_failed)
    say(_("К скачиванию: {0}").format(len(pending)))
    counts = {"downloaded": 0, "failed": 0, "unavailable": 0}
    for i, row in enumerate(pending, 1):
        if STOP.is_set():
            raise Cancelled()
        progress(i, len(pending), _("Скачивание {0}/{1} (пост {2})").format(i, len(pending), row['post_id']))
        try:
            status, note = download_post(db, root, row)
        except Cancelled:
            raise
        except Exception as e:
            log.warning("Ошибка загрузки поста %s: %s", row["post_id"], e)
            status, note = "failed", str(e)
        db.set_post(row["post_id"], status, note)
        counts[status] = counts.get(status, 0) + 1
        if status != "downloaded":
            say(_("Пост {0}: {1} ({2})").format(row['post_id'], status, note), "warn")
    say(_("Готово. Скачано: {0}, ошибок: {1}, недоступно: {2}").format(counts['downloaded'], counts['failed'], counts['unavailable']))
    return counts
