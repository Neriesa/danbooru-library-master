# -*- coding: utf-8 -*-
"""Шаг 4: результаты и действия."""

import tkinter as tk
import webbrowser
from collections import Counter
from pathlib import Path
from tkinter import messagebox, ttk


from .actions import add_favorites_batch, remove_favorites_batch
from .config import developer_mode
from .constants import ALL_LABEL, CATEGORY_LABELS, CATEGORY_ORDER, MARK_BY_CATEGORY, NOTFOUND_PREFIX, OTHER_DIR, SITE_DELETED_PREFIX, TRASH_DIR
from .files import open_in_system
from .dialogs import preview_moves
from .mover import move_marked, plan_moves, undo_moves
from .site import build_results, post_url, write_html_report
from .theme import BG, BG2, FG, GREEN, MUTED, RED, TEAL
from .i18n import _


class Step4Mixin:
    # ---------- шаг 4 ----------
    COLUMNS = (("status", _("Статус"), 210), ("file", _("Файл"), 380), ("post", _("Пост"), 70),
               ("artist", _("Автор"), 150), ("character", _("Персонаж"), 150), ("note", _("Заметка"), 300))

    def render_step_4(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=_("Результаты"), font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=2)
        self.lbl_summary = tk.Label(f, text="", bg=BG, fg=MUTED, font=("Arial", 10))
        self.lbl_summary.pack()

        flt = tk.Frame(f, bg=BG)
        flt.pack(fill="x", pady=4)
        tk.Label(flt, text=_("Показать:"), bg=BG, fg=FG).pack(side="left", padx=4)
        self.cmb_cat = ttk.Combobox(flt, state="readonly", width=34,
                                    values=[ALL_LABEL] + [CATEGORY_LABELS[c] for c in CATEGORY_ORDER])
        self.cmb_cat.set(ALL_LABEL)
        self.cmb_cat.pack(side="left", padx=4)
        self.cmb_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())
        tk.Label(flt, text=_("Поиск (файл, автор, персонаж, серия):"), bg=BG, fg=FG).pack(side="left", padx=8)
        self.var_q = tk.StringVar()
        self.var_q.trace_add("write", lambda *a: self.refresh_tree())
        tk.Entry(flt, textvariable=self.var_q, width=30, bg=BG2, fg=FG, insertbackground=FG,
                 relief="flat").pack(side="left", padx=4)

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, columns=[c[0] for c in self.COLUMNS], show="headings", selectmode="extended")
        for key, title, width in self.COLUMNS:
            self.tree.heading(key, text=title, command=lambda k=key: self.sort_tree(k))
            self.tree.column(key, width=width, anchor="w")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.open_selected_post())

        r1 = tk.Frame(f, bg=BG)
        r1.pack(fill="x", pady=(6, 0))
        self.button(r1, _("Выбрать все «не в Favorites»"), lambda: self.select_category("not_fav"))
        self.button(r1, _("Выбрать все «не найдено»"), lambda: self.select_category("not_found"))
        self.button(r1, _("Выбрать все «удалён на сайте»"), lambda: self.select_category("deleted"))
        self.button(r1, _("Открыть пост на сайте"), self.open_selected_post)
        self.button(r1, _("Показать файл"), self.open_selected_file)
        if developer_mode():
            self.button(r1, _("HTML-отчёт"), self.action_html_report, TEAL)
        r2 = tk.Frame(f, bg=BG)
        r2.pack(fill="x", pady=4)
        self.btn_fav = self.button(r2, _("Добавить выбранные в Favorites"), self.action_add_favorites, GREEN, bold=True)
        self.btn_nf = self.button(r2, _("Выбранные «не найдено»/«удалён» → other/"), self.action_move_notfound, "#ef6c00")
        self.button(r2, _("Вернуть из other/ (notFound_, siteDeleted_)"), lambda: self.action_undo("move_notfound"))
        self.button(r2, _("Вернуть из deleted"), lambda: self.action_undo("move_deleted"))
        self.button(r2, _("К докачке ➔"), lambda: self.goto_step(5), TEAL, side="right")
        r3 = tk.Frame(f, bg=BG)
        r3.pack(fill="x", pady=(0, 4))
        self.button(r3, _("Убрать выбранные из Favorites → deleted"), self.action_remove_favorites, RED)
        tk.Label(r3, text=_("Отметка снимается на сайте, файл уходит в deleted/<id>. Передумали: положите файл обратно в папку."),
                 bg=BG, fg=MUTED, font=("Arial", 9)).pack(side="left", padx=8)

        self.pb = ttk.Progressbar(f, orient="horizontal", mode="determinate")
        self.pb.pack(fill="x", pady=2)
        self.lbl_detail = tk.Label(f, text="", bg=BG, fg=MUTED, font=("Arial", 9))
        self.lbl_detail.pack()
        self.load_results()

    def load_results(self):
        self.results = build_results(self.db, self.root_path)
        counts = Counter(r["category"] for r in self.results)
        if not self.results:
            self.lbl_summary.config(text=_("Данных пока нет: сначала выполните шаг 3 (сверку)."))
        else:
            self.lbl_summary.config(text=" | ".join(
                f"{CATEGORY_LABELS[c]}: {counts[c]}" for c in CATEGORY_ORDER if counts[c]))
        self.refresh_tree()

    def refresh_tree(self):
        if self.tree is None:
            return
        cat, q = self.cmb_cat.get(), self.var_q.get().strip().lower()
        rows = []
        for r in self.results:
            if cat != ALL_LABEL and r["label"] != cat:
                continue
            if q and q not in r["search"]:
                continue
            rows.append(r)
        self.populate(rows)

    def populate(self, rows):
        self.view_rows = rows
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            self.tree.insert("", "end", iid=str(i), values=(
                r["label"], r["rel"], r["post_id"] or "", r["artist"], r["character"], r["note"]))

    def sort_tree(self, key):
        idx = [c[0] for c in self.COLUMNS].index(key)

        def sort_val(r):
            v = [r["label"], r["rel"], r["post_id"] or 0, r["artist"], r["character"], r["note"]][idx]
            return (0, v) if isinstance(v, int) else (1, str(v).lower())

        self.populate(sorted(self.view_rows, key=sort_val))

    def selected_rows(self):
        return [self.view_rows[int(i)] for i in self.tree.selection()]

    def select_category(self, cat):
        ids = [str(i) for i, r in enumerate(self.view_rows) if r["category"] == cat]
        if not ids:
            messagebox.showinfo(_("Нет строк"), _("В текущем списке нет таких файлов. Проверьте фильтр «Показать»."))
            return
        self.tree.selection_set(ids)

    def open_selected_post(self):
        rows = self.selected_rows()
        if rows and rows[0]["post_id"]:
            webbrowser.open(post_url(rows[0]["post_id"]))
        elif rows:
            messagebox.showinfo(_("Нет поста"), _("Для этого файла пост на Danbooru не найден."))

    def open_selected_file(self):
        rows = self.selected_rows()
        if rows:
            open_in_system(Path(rows[0]["filepath"]))

    def action_html_report(self):
        p = write_html_report(self.svc_dir, self.results)
        webbrowser.open(p.as_uri())

    def finish_action(self, status, text):
        self.progress(1, 1, text if status == "ok" else _("Остановлено или ошибка (см. booru_library.log)"))
        self.load_results()

    def action_add_favorites(self):
        if self.busy:
            return
        rows = self.selected_rows()
        ids = sorted({r["post_id"] for r in rows if r["post_id"] and r["category"] == "not_fav"})
        skipped = len(rows) - len([r for r in rows if r["post_id"] and r["category"] == "not_fav"])
        if not ids:
            messagebox.showinfo(_("Нечего добавлять"), _("Выделите строки со статусом «Есть на сайте, не в Favorites»."))
            return
        if not messagebox.askyesno(
                _("Добавление в Favorites"),
                _("Будет добавлено постов в Favorites: {0}.\n").format(len(ids))
                + (_("Пропущено выделенных строк другого статуса: {0}.\n").format(skipped) if skipped else "")
                + _("\nЭто изменит ваш аккаунт на Danbooru. Продолжить?")):
            return

        def work():
            add_favorites_batch(self.db, ids, self.say, self.progress)

        self.start_worker(work, lambda st: self.finish_action(st, _("Добавление завершено")))

    def action_remove_favorites(self):
        if self.busy:
            return
        rows = [r for r in self.selected_rows() if r["post_id"] and r["category"] in ("fav", "deleted")]
        if not rows:
            messagebox.showinfo(_("Нечего убирать"), _("Выделите строки со статусом «В Favorites» "
                                                  "или «Пост удалён/забанен на сайте»."))
            return
        by_post = {}
        for r in rows:
            by_post.setdefault(r["post_id"], r["md5"])
        n_fav = sum(1 for pid in by_post if (self.db.post_by_id(pid) or {}).get("is_fav"))
        n_files = sum(1 for r in self.results if r["post_id"] in by_post)
        if not messagebox.askyesno(
                _("Убрать из Favorites"),
                _("С Favorites на сайте будет снято постов: {0}.\nФайлов будет перенесено в {1}/ (имя <id>.<расширение>): {2}.\n\nПередумать можно так: положите файл обратно в папку, и при следующей сверке он снова станет «не в Favorites» (или кнопка «Вернуть из deleted»).\n\nЭто изменит ваш аккаунт на Danbooru. Продолжить?").format(n_fav, TRASH_DIR, n_files)):
            return
        items = list(by_post.items())

        def work():
            remove_favorites_batch(self.db, self.root_path, items, self.say, self.progress)

        self.start_worker(work, lambda st: self.finish_action(st, _("Готово")))

    def action_move_notfound(self):
        if self.busy:
            return
        rows = [r for r in self.selected_rows() if r["category"] in MARK_BY_CATEGORY]
        if not rows:
            messagebox.showinfo(_("Нечего переносить"),
                                _("Выделите строки со статусом «Не найдено» или «Пост удалён/забанен на сайте»."))
            return
        items = [(r["filepath"], r["category"]) for r in rows]
        if not preview_moves(self.root, plan_moves(self.root_path, items),
                             _("Перенос в {0}/ ({1} / {2})").format(OTHER_DIR, NOTFOUND_PREFIX, SITE_DELETED_PREFIX)):
            return

        def work():
            move_marked(self.db, self.root_path, items, self.say, self.progress)

        self.start_worker(work, lambda st: self.finish_action(st, _("Перенос завершён")))

    def action_undo(self, kind):
        if self.busy:
            return
        n = len(self.db.undo_candidates(kind))
        if not n:
            messagebox.showinfo(_("Нечего возвращать"), _("В журнале нет перемещений, которые можно отменить."))
            return
        if not messagebox.askyesno(_("Вернуть файлы"), _("Вернуть на прежние места файлов: {0}?").format(n)):
            return
        restored, skipped = undo_moves(self.db, kind, self.say)
        messagebox.showinfo(_("Готово"), _("Возвращено: {0}, пропущено: {1}").format(restored, skipped))
        self.load_results()
