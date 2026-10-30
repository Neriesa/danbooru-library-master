# -*- coding: utf-8 -*-

import html
import time
from collections import Counter
from pathlib import Path


from .constants import BASE_URL, CATEGORY_LABELS, CATEGORY_ORDER, MARK_BY_CATEGORY, OTHER_DIR
from .net import Cancelled, STOP, api_json, lookup_md5, post_to_row
from .db import LibraryDB
from .files import managed_post_id
from .dupes import scan_library
from .mover import move_marked
from .i18n import _


def list_favorites(db: LibraryDB, username: str, full: bool, say, progress):
    """Обновляет таблицу posts списком Избранного. Постранично, новые первыми."""
    complete_before = db.get_meta("listing_complete") == "1"
    incremental = complete_before and not full
    say(_("Читаю список Избранного (только новые)…") if incremental else _("Читаю весь список Избранного…"))
    if not incremental:
        db.reset_fav_seen()
    tags = f"ordfav:{username}"
    page, total_seen, total_new = 1, 0, 0
    reached_end = False
    while page <= 1000:
        if STOP.is_set():
            raise Cancelled()
        data = api_json("/posts.json", {"tags": tags, "limit": 100, "page": page})
        if not data and page == 1 and tags.startswith("ordfav:"):
            say(_("ordfav ничего не вернул, пробую fav:…"), "warn")
            tags = f"fav:{username}"
            continue
        if not data:
            reached_end = True
            break
        new = db.upsert_posts([post_to_row(p) for p in data], favorites=True)
        total_seen += len(data)
        total_new += new
        progress(page, 0, _("Список Избранного: страница {0}, постов {1}").format(page, total_seen))
        if incremental and new == 0:
            break
        page += 1
    if reached_end:
        db.set_meta("listing_complete", "1")
        if not incremental:
            dropped = db.finish_full_listing()
            if dropped:
                say(_("Постов, которых больше нет в Избранном: {0}").format(dropped))
    say(_("Список Избранного обновлён: просмотрено {0}, новых {1}").format(total_seen, total_new))


def check_against_danbooru(db: LibraryDB, root: Path, username: str, full_listing: bool,
                           recheck: bool, auto_notfound: bool, say, progress):
    """Определяет для каждого уникального MD5 локальных файлов, что с ним на Danbooru."""
    scan_library(db, root, say, progress)
    list_favorites(db, username, full_listing, say, progress)

    # 1) файлы, чей пост известен без запросов (скачаны скриптом / найдены раньше)
    n_known = 0
    for r in db.known_id_unmatched():
        post = db.post_by_id(r["danbooru_id"])
        if post or managed_post_id(Path(r["filepath"]), root):
            db.set_match(r["md5"], "found", r["danbooru_id"])
            n_known += 1
    if n_known:
        say(_("Пост известен без запросов: {0}").format(n_known))

    # 2) остальные: сначала по таблице posts (Favorites уже там), потом один запрос на уникальный MD5
    todo = db.unchecked_md5s(recheck)
    say(_("Уникальных MD5 к проверке: {0}").format(len(todo)))
    counts = Counter()
    for i, md5 in enumerate(todo, 1):
        if STOP.is_set():
            raise Cancelled()
        progress(i, len(todo), _("Проверка MD5 {0}/{1}").format(i, len(todo)))
        post_row = db.post_by_md5(md5)
        if post_row:
            counts[_("из списка Избранного/кэша")] += 1
        else:
            post = lookup_md5(md5)
            if post:
                db.upsert_posts([post_to_row(post)], favorites=False)
                post_row = db.post_by_id(post["id"])
                counts[_("найдено запросом")] += 1
        if post_row:
            db.set_match(md5, "found", post_row["post_id"])
            db.set_files_found(md5, post_row["post_id"], post_row["rating"])
        else:
            db.set_match(md5, "not_found")
            db.set_files_not_found(md5)
            counts[_("не найдено")] += 1
    say(_("Итог проверки: ") + (", ".join(f"{k}: {v}" for k, v in counts.items()) or _("новых файлов нет")))

    # 3) «не найдено» и «удалён на сайте» -> other/ с пометкой в имени
    #    (обратимо; файлы, которые вы вернули вручную, не трогаются)
    if auto_notfound:
        todo_marked = pending_moves(db, root)
        if todo_marked:
            move_marked(db, root, todo_marked, say, progress)
    else:
        left = len(pending_moves(db, root))
        if left:
            say(_("Файлов, которые можно перенести в {0}/ с пометкой: {1} (ничего не перенесено)").format(OTHER_DIR, left))



def pending_moves(db: LibraryDB, root: Path):
    """Файлы, которые по итогам сверки стоит перенести в other/: [(путь, категория)].
    Уже перенесённые и те, что вы вернули вручную (keep), пропускаются."""
    todo = []
    for r in build_results(db, root):
        mark = MARK_BY_CATEGORY.get(r["category"])
        if not mark or r["keep"]:
            continue
        p = Path(r["filepath"])
        if p.parent == root / OTHER_DIR and p.name.startswith(mark):
            continue
        todo.append((r["filepath"], r["category"]))
    return todo


def derive_category(row: dict) -> str:
    st = row["state"]
    if st is None:
        return "unchecked"
    if st == "not_found":
        return st
    if row["deleted"]:
        return "deleted"
    return "fav" if row["is_fav"] else "not_fav"


def build_results(db: LibraryDB, root: Path):
    out = []
    for r in db.matches_view():
        cat = derive_category(r)
        note = ""
        if cat == "deleted":
            note = _("пост удалён или забанен: скачать оригинал может быть нельзя")
        p = Path(r["filepath"])
        try:
            rel = str(p.relative_to(root))
        except ValueError:
            rel = str(p)
        item = {
            "filepath": r["filepath"], "rel": rel, "category": cat, "label": CATEGORY_LABELS[cat],
            "post_id": r["post_id"], "artist": r["artist"] or "", "character": r["character"] or "",
            "copyright": r["copyright"] or "", "note": note, "md5": r["md5"], "keep": bool(r.get("keep")),
        }
        item["search"] = " ".join([rel, item["artist"], item["character"], item["copyright"], note]).lower()
        out.append(item)
    out.sort(key=lambda x: (CATEGORY_ORDER.index(x["category"]), x["artist"], x["rel"]))
    return out


def post_url(post_id) -> str:
    return f"{BASE_URL}/posts/{post_id}"


def write_html_report(out_dir: Path, results) -> Path:
    esc = html.escape
    by_cat = {c: [] for c in CATEGORY_ORDER}
    for r in results:
        by_cat[r["category"]].append(r)

    def table(rows):
        out = [_('<table><tr><th>Файл</th><th>Пост</th><th>Автор</th><th>Персонажи</th><th>Серия</th><th>Заметка</th></tr>')]
        for r in rows:
            p = Path(r["filepath"])
            link = f'<a href="{esc(p.as_uri())}">{esc(p.name)}</a><br><small>{esc(r["rel"])}</small>'
            pl = f'<a href="{post_url(r["post_id"])}" target="_blank">#{r["post_id"]}</a>' if r["post_id"] else ""
            out.append(f'<tr><td>{link}</td><td>{pl}</td><td>{esc(r["artist"])}</td>'
                       f'<td>{esc(r["character"])}</td><td>{esc(r["copyright"])}</td><td>{esc(r["note"])}</td></tr>')
        out.append("</table>")
        return "\n".join(out)

    parts = [_("<!doctype html><html><head><meta charset='utf-8'><title>Отчёт Danbooru Library Master</title>"),
             "<style>body{background:#1a1a1a;color:#eee;font-family:Arial;margin:20px}"
             "a{color:#80cbc4}table{border-collapse:collapse;width:100%;margin-bottom:24px}"
             "td,th{border:1px solid #444;padding:4px 8px;text-align:left;vertical-align:top;font-size:13px}"
             "th{background:#2d2d2d}h2{margin-top:30px}input{padding:6px;width:300px}small{color:#999}</style>",
             "<script>function f(q){q=q.toLowerCase();document.querySelectorAll('tr.r').forEach(function(t){"
             "t.style.display=t.innerText.toLowerCase().indexOf(q)>=0?'':'none'})}</script></head><body>",
             _("<h1>Отчёт ({0})</h1>").format(time.strftime('%Y-%m-%d %H:%M')),
             _("<p>Поиск по отчёту: <input oninput='f(this.value)' placeholder='автор, персонаж, имя файла…'></p><ul>")]
    for c in CATEGORY_ORDER:
        if by_cat[c]:
            parts.append(f"<li>{esc(CATEGORY_LABELS[c])}: <b>{len(by_cat[c])}</b></li>")
    parts.append("</ul>")
    for c in CATEGORY_ORDER:
        rows = by_cat[c]
        if not rows:
            continue
        body = table(rows).replace("<tr><td>", "<tr class='r'><td>")
        head = f"<h2>{esc(CATEGORY_LABELS[c])} ({len(rows)})</h2>"
        parts.append(f"<details><summary>{head}</summary>{body}</details>" if c == "fav" else head + body)
    parts.append("</body></html>")
    path = out_dir / "report.html"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
