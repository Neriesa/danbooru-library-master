# -*- coding: utf-8 -*-

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from .constants import HASH_WORKERS, IMAGE_EXT
from .config import log
from .net import Cancelled, STOP
from .db import LibraryDB
from .files import iter_library_files, managed_post_id
from .imaging import get_resolution, hash_file
from .i18n import _


def scan_library(db: LibraryDB, root: Path, say, progress, workers=HASH_WORKERS):
    """Обновляет в базе MD5/pHash. Хэшируются только новые и изменённые файлы."""
    say(_("Обход папки…"))
    files = list(iter_library_files(root))
    cached = db.load_files()

    present = {str(p) for p in files}
    gone = [p for p in cached if p not in present]
    if gone:
        db.delete_files(gone)
        say(_("Из базы убраны записи о пропавших/перемещённых файлах: {0}").format(len(gone)))

    todo = []
    for p in files:
        try:
            st = p.stat()
        except OSError:
            continue
        c = cached.get(str(p))
        unchanged = (
            c and c["filesize"] == st.st_size and abs((c["mtime"] or 0) - st.st_mtime) < 1e-3
            and c["md5"] and (c["phash"] or "") != ""
        )
        if unchanged and managed_post_id(p, root) and c["status"] != "found":
            unchanged = False
        if not unchanged:
            todo.append(p)

    say(_("Файлов в папке: {0}, нужно обработать: {1}").format(len(files), len(todo)))
    if not todo:
        progress(1, 1, _("Все хэши актуальны"))
        return len(files)

    done, batch = 0, []
    ex = ThreadPoolExecutor(max_workers=workers)
    futures = {}
    try:
        futures = {ex.submit(hash_file, p, root): p for p in todo}
        for fut in as_completed(futures):
            if STOP.is_set():
                raise Cancelled()
            p = futures[fut]
            try:
                batch.append(fut.result())
            except Exception as e:
                log.warning("Ошибка обработки %s: %s", p, e)
                say(_("Пропущен {0}: {1}").format(p.name, e), "warn")
            done += 1
            progress(done, len(todo), _("Хэши: {0}").format(p.name))
            if len(batch) >= 100:
                db.upsert_many(batch)
                batch = []
    finally:
        for f in futures:
            f.cancel()
        ex.shutdown(wait=True)
        if batch:
            db.upsert_many(batch)
    return len(files)



POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def cluster_by_phash(units, threshold):
    """
    Группировка "звездой": самая тяжёлая картинка - центр, к ней присоединяются похожие именно на неё.
    Цепочки A~B~C не склеиваются. units: [{"phash": int, "size": int}].
    Возвращает [[(индекс, расстояние), ...], ...]
    """
    n = len(units)
    order = sorted(range(n), key=lambda i: -units[i]["size"])
    assigned = [False] * n
    clusters = []
    arr = np.array([u["phash"] for u in units], dtype=np.uint64)
    for i in order:
        if assigned[i]:
            continue
        assigned[i] = True
        cluster = [(i, 0)]
        dist = POP8[(arr ^ arr[i]).view(np.uint8).reshape(-1, 8)].sum(axis=1)
        for j in np.nonzero(dist <= threshold)[0]:
            j = int(j)
            if not assigned[j]:
                assigned[j] = True
                cluster.append((j, int(dist[j])))
        clusters.append(cluster)
    return clusters


def find_duplicate_groups(db: LibraryDB, threshold: int, use_phash: bool, say):
    records = []
    for r in db.dup_records():
        p = Path(r["filepath"])
        if p.exists():
            records.append({**r, "path": p})
    say(_("Файлов для сравнения: {0}").format(len(records)))

    by_md5 = {}
    for r in records:
        by_md5.setdefault(r["md5"], []).append(r)

    units, no_hash_units = [], []
    for md5, members in by_md5.items():
        phash = None
        if use_phash:
            for m in members:
                ph = m["phash"]
                if ph and ph != "-" and m["path"].suffix.lower() in IMAGE_EXT:
                    try:
                        phash = int(ph, 16)
                        break
                    except ValueError:
                        pass
        unit = {"members": members, "phash": phash, "size": max(m["filesize"] or 0 for m in members)}
        (units if phash is not None else no_hash_units).append(unit)

    raw_groups = []
    for u in no_hash_units:  # видео, архивы: только точные копии
        if len(u["members"]) >= 2:
            raw_groups.append(("exact", [(m, 0) for m in u["members"]]))

    for cluster in cluster_by_phash(units, threshold):
        if len(cluster) == 1:
            u = units[cluster[0][0]]
            if len(u["members"]) >= 2:
                raw_groups.append(("exact", [(m, 0) for m in u["members"]]))
        else:
            members = []
            for idx, dist in cluster:
                members.extend((m, dist) for m in units[idx]["members"])
            raw_groups.append(("similar", members))

    groups = []
    for kind, members in raw_groups:
        items = []
        for m, dist in members:
            w, h = get_resolution(m["path"])
            items.append({"path": m["path"], "md5": m["md5"], "dist": dist, "w": w, "h": h,
                          "size": m["filesize"] or 0, "dbid": m["danbooru_id"]})
        groups.append({"kind": kind, "members": items})
    groups.sort(key=lambda g: (g["kind"] != "exact", -len(g["members"])))
    say(_("Найдено групп: {0} (точных: {1})").format(len(groups), sum(g['kind'] == 'exact' for g in groups)))
    return groups


def rank_key(m):
    """Что рекомендуется оставить: подтверждён на Danbooru > больше разрешение > больше размер."""
    return (1 if m["dbid"] else 0, m["w"] * m["h"], m["size"])


def write_duplicates_report(out_dir: Path, groups) -> Path:
    path = out_dir / "duplicates_report.txt"
    lines = [_("Отчёт о дубликатах ({0})").format(time.strftime('%Y-%m-%d %H:%M')), _("Групп: {0}").format(len(groups)), ""]
    for i, g in enumerate(groups, 1):
        label = _("точные копии (MD5)") if g["kind"] == "exact" else _("похожие (pHash)")
        lines.append(_("=== Группа {0}: {1}, файлов: {2} ===").format(i, label, len(g['members'])))
        for m in sorted(g["members"], key=rank_key, reverse=True):
            extra = f", ID Danbooru {m['dbid']}" if m["dbid"] else ""
            lines.append(_("  {0} | {1}x{2} | {3:.1f} KB | расстояние {4}{5}").format(m['path'], m['w'], m['h'], m['size'] / 1024, m['dist'], extra))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
