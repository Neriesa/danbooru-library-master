# -*- coding: utf-8 -*-
"""Шаг 6: мои теги."""

import tkinter as tk
from tkinter import messagebox, ttk


from .actions import compute_tag_stats, refresh_tag_data
from .config import developer_mode, get_credentials
from .constants import TAG_KINDS
from .net import STOP
from .theme import BG, FG, GREEN, MUTED, RED
from .i18n import _


class Step6Mixin:
    # ---------- шаг 6: мои теги ----------
    def render_step_6(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=_("Мои теги"), font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=4)
        tk.Label(f, text=_("Топ по вашему избранному. Всё лишнее (теги качества, служебные) выделите и нажмите "
                         "«Скрыть выбранные»: на их место встанут следующие.\nСписок сохраняется и дальше "
                         "будет основой для подборки новых постов."), fg=MUTED, bg=BG, font=("Arial", 10),
                 justify="center").pack()
        self.lbl_tagsum = tk.Label(f, text="", bg=BG, fg=MUTED, font=("Arial", 9))
        self.lbl_tagsum.pack(pady=2)

        ctrl = tk.Frame(f, bg=BG)
        ctrl.pack(pady=4)
        tk.Label(ctrl, text=_("Обновить теги по последним"), bg=BG, fg=FG).pack(side="left")
        self.spin_tags = tk.Spinbox(ctrl, from_=100, to=20000, increment=100, width=7, command=self.update_tag_estimate)
        self.spin_tags.delete(0, "end")
        self.spin_tags.insert(0, "1000")
        self.spin_tags.pack(side="left", padx=4)
        self.lbl_tag_est = tk.Label(ctrl, text="", bg=BG, fg=MUTED)
        self.lbl_tag_est.pack(side="left")
        self.btn_tags = self.button(ctrl, _("Обновить теги"), self.start_tag_refresh, GREEN, bold=True)
        self.button(ctrl, _("Остановить"), STOP.set, RED)
        self.update_tag_estimate()

        grid = tk.Frame(f, bg=BG)
        grid.pack(fill="both", expand=True, pady=6)
        self.tag_trees = {}
        for col, (kind, title) in enumerate(TAG_KINDS):
            box = tk.LabelFrame(grid, text=title, bg=BG, fg=FG, font=("Arial", 10, "bold"))
            box.grid(row=0, column=col, padx=5, sticky="nsew")
            grid.columnconfigure(col, weight=1)
            tree = ttk.Treeview(box, columns=("tag", "n", "pct"), show="headings", height=10, selectmode="extended")
            tree.heading("tag", text=_("Тег"))
            tree.heading("n", text=_("Постов"))
            tree.heading("pct", text=_("Доля"))
            tree.column("tag", width=170, anchor="w")
            tree.column("n", width=55, anchor="e")
            tree.column("pct", width=50, anchor="e")
            tree.pack(fill="both", expand=True, padx=3, pady=3)
            self.tag_trees[kind] = tree

        row = tk.Frame(f, bg=BG)
        row.pack(pady=4)
        self.button(row, _("Скрыть выбранные"), self.hide_selected_tags, "#ef6c00", bold=True)
        self.button(row, _("Скрытые теги…"), self.show_hidden_tags)
        self.pb = ttk.Progressbar(f, orient="horizontal", mode="determinate")
        self.pb.pack(fill="x", pady=2)
        self.lbl_detail = tk.Label(f, text="", bg=BG, fg=MUTED, font=("Arial", 9))
        self.lbl_detail.pack()
        self.refresh_tag_stats()

    def update_tag_estimate(self):
        try:
            n = max(100, int(self.spin_tags.get()))
        except ValueError:
            n = 1000
        self.lbl_tag_est.config(text=_("избранных (≈ {0} запросов)").format(-(-n // 100)))

    def refresh_tag_stats(self):
        stats = compute_tag_stats(self.db, 10)
        for kind, tree in self.tag_trees.items():
            tree.delete(*tree.get_children())
            for tag, n, pct in stats[kind]["top"]:
                tree.insert("", "end", iid=tag, values=(tag, n, f"{pct:.0f}%"))
        total = len(self.db.favorite_tag_rows())
        g = stats["tags_general"]["posts"]
        a = stats["artist"]["posts"]
        if not total:
            self.lbl_tagsum.config(text=_("Избранное в базе пусто: выполните сверку (шаг 3) или нажмите «Обновить теги»."))
        elif developer_mode():
            self.lbl_tagsum.config(text=_("В базе избранных постов: {0}. С тегами художников/серий: {1}, с общими тегами: {2}. Чтобы учесть больше, нажмите «Обновить теги».").format(total, a, g))
        else:
            self.lbl_tagsum.config(text="")

    def start_tag_refresh(self):
        if self.busy:
            return
        try:
            n = max(100, int(self.spin_tags.get()))
        except ValueError:
            n = 1000
        user, _key = get_credentials()
        self.btn_tags.config(state="disabled")

        def work():
            refresh_tag_data(self.db, user, n, self.say, self.progress)

        def done(status):
            self.btn_tags.config(state="normal")
            self.progress(1, 1, {"ok": _("Теги обновлены"), "cancelled": _("Остановлено"),
                                 "error": _("Ошибка (см. журнал)")}[status])
            self.refresh_tag_stats()

        self.start_worker(work, done)

    def hide_selected_tags(self):
        tags = [t for tree in self.tag_trees.values() for t in tree.selection()]
        if not tags:
            messagebox.showinfo(_("Ничего не выбрано"), _("Выделите теги в списках (можно несколько, с Ctrl)."))
            return
        self.db.ignore_tags(tags)
        self.refresh_tag_stats()

    def show_hidden_tags(self):
        win = tk.Toplevel(self.root)
        win.title(_("Скрытые теги"))
        win.geometry("360x460")
        win.configure(bg=BG)
        tk.Label(win, text=_("Эти теги не попадают в топ. Выделите и нажмите «Вернуть»."), bg=BG, fg=FG,
                 wraplength=330).pack(pady=6)
        box = tk.Listbox(win, selectmode="extended", bg="#222222", fg=FG, selectbackground="#00695c")
        box.pack(fill="both", expand=True, padx=8)
        for t in sorted(self.db.ignored_tags()):
            box.insert("end", t)

        def restore():
            tags = [box.get(i) for i in box.curselection()]
            if tags:
                self.db.unignore_tags(tags)
                for i in reversed(box.curselection()):
                    box.delete(i)
                self.refresh_tag_stats()

        self.button(win, _("Вернуть выбранные"), restore, GREEN, side="bottom", bold=True)
