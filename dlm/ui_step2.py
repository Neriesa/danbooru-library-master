# -*- coding: utf-8 -*-
"""Шаг 2: дубликаты."""

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import ImageTk

from .config import developer_mode, log
from .constants import DEFAULT_PHASH_THRESHOLD, TRASH_DIR
from .dupes import find_duplicate_groups, rank_key, scan_library, write_duplicates_report
from .files import move_file, open_in_system
from .imaging import load_preview
from .theme import BG, BG2, FG, GREEN, GREY, MUTED, RED, TEAL
from .i18n import _


class Step2Mixin:
    # ---------- шаг 2 ----------
    def render_step_2(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=_("Дубликаты"), font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=4)
        tk.Label(f, text=_("Сначала считаются хэши новых файлов (при первом запуске это долго), потом показываются группы. "
                         "Ничего не удаляется автоматически. Кнопка «В deleted» переносит файл в папку deleted; "
                         "вернуть можно на шаге 4."), fg=MUTED, bg=BG, font=("Arial", 9)).pack()

        ctrl = tk.Frame(f, bg=BG)
        ctrl.pack(pady=6)
        self.var_phash = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text=_("Искать и похожие картинки (pHash)"), variable=self.var_phash, bg=BG, fg=FG,
                       selectcolor=BG2, activebackground=BG, activeforeground=FG).pack(side="left", padx=8)
        tk.Label(ctrl, text=_("Порог похожести (0-12):"), bg=BG, fg=FG).pack(side="left")
        self.spin_thr = tk.Spinbox(ctrl, from_=0, to=12, width=4)
        self.spin_thr.delete(0, "end")
        self.spin_thr.insert(0, str(DEFAULT_PHASH_THRESHOLD))
        self.spin_thr.pack(side="left", padx=4)
        self.btn_start2 = self.button(ctrl, _("Найти дубликаты"), self.start_step2, GREEN, bold=True)

        self.lbl_detail = tk.Label(f, text=_("Нажмите «Найти дубликаты»."), bg=BG, fg=MUTED)
        self.lbl_detail.pack()
        self.pb = ttk.Progressbar(f, orient="horizontal", mode="determinate")
        self.pb.pack(fill="x", pady=4)
        self.dup_area = tk.Frame(f, bg=BG)
        self.dup_area.pack(fill="both", expand=True)

    def start_step2(self):
        if self.busy:
            return
        try:
            thr = max(0, min(12, int(self.spin_thr.get())))
        except ValueError:
            thr = DEFAULT_PHASH_THRESHOLD
        use_phash = self.var_phash.get()
        self.btn_start2.config(state="disabled")
        result = {}

        def work():
            scan_library(self.db, self.root_path, self.say, self.progress)
            self.progress(0, 0, _("Сравнение файлов…"))
            result["groups"] = find_duplicate_groups(self.db, thr, use_phash, self.say)
            if result["groups"] and developer_mode():
                write_duplicates_report(self.svc_dir, result["groups"])

        def done(status):
            self.btn_start2.config(state="normal")
            if status != "ok":
                self.lbl_detail.config(text=_("Остановлено или ошибка (см. booru_library.log)"))
                return
            self.dup_groups = result.get("groups", [])
            self.dup_idx = 0
            self.pb.config(mode="determinate", value=0)
            self.render_group()

        self.start_worker(work, done)

    def render_group(self):
        for w in self.dup_area.winfo_children():
            w.destroy()
        self.photos.clear()

        self.dup_groups = [g for g in self.dup_groups if len(g["members"]) >= 2]
        if not self.dup_groups:
            self.lbl_detail.config(text=_("Дубликатов не найдено (или все обработаны)."))
            self.button(self.dup_area, _("Перейти к шагу 3 ➔"), lambda: self.goto_step(3), GREEN, side="top")
            return
        self.dup_idx = max(0, min(self.dup_idx, len(self.dup_groups) - 1))
        g = self.dup_groups[self.dup_idx]
        label = _("точные копии (MD5)") if g["kind"] == "exact" else _("похожие (pHash)")
        self.lbl_detail.config(text=_("Группа {0} из {1}: {2}, файлов: {3}").format(self.dup_idx + 1, len(self.dup_groups), label, len(g['members'])))

        ranked = sorted(g["members"], key=rank_key, reverse=True)
        grid = tk.Frame(self.dup_area, bg=BG)
        grid.pack(fill="both", expand=True)
        for idx, m in enumerate(ranked):
            card = tk.Frame(grid, bg=BG2, bd=2, relief="groove")
            card.grid(row=idx // 4, column=idx % 4, padx=8, pady=8, sticky="n")
            if idx == 0:
                badge, color = _("РЕКОМЕНДУЕТСЯ ОСТАВИТЬ"), GREEN
            elif g["kind"] == "exact" or m["dist"] == 0:
                badge, color = _("ТОЧНАЯ КОПИЯ"), RED
            else:
                badge, color = _("ПОХОЖЕЕ (расстояние {0})").format(m['dist']), "#ef6c00"
            tk.Label(card, text=badge, bg=color, fg="white", font=("Arial", 9, "bold")).pack(fill="x")

            img = load_preview(m["path"])
            if img:
                photo = ImageTk.PhotoImage(img)
                self.photos.append(photo)
                tk.Label(card, image=photo, bg="black").pack(padx=6, pady=6)
            else:
                tk.Label(card, text=_("Превью недоступно"), bg="black", fg=MUTED, width=28, height=10).pack(padx=6, pady=6)

            try:
                shown = m["path"].relative_to(self.root_path)
            except ValueError:
                shown = m["path"]
            info = f"{shown}\n{m['w']}x{m['h']} | {m['size'] / 1024:.1f} KB"
            if m["dbid"]:
                info += _("\n✔ есть на Danbooru (ID {0})").format(m['dbid'])
            tk.Label(card, text=info, bg=BG2, fg=FG, font=("Arial", 8), wraplength=230, justify="left").pack(padx=4)
            row = tk.Frame(card, bg=BG2)
            row.pack(pady=6)
            tk.Button(row, text=_("Открыть"), command=lambda p=m["path"]: open_in_system(p), bg=GREY, fg="white",
                      relief="flat", font=("Arial", 9)).pack(side="left", padx=3)
            tk.Button(row, text=_("В deleted"), command=lambda mm=m: self.delete_member(mm), bg=RED, fg="white",
                      relief="flat", font=("Arial", 9)).pack(side="left", padx=3)

        nav = tk.Frame(self.dup_area, bg=BG)
        nav.pack(side="bottom", fill="x", pady=8)
        self.button(nav, _("⬅ Назад"), lambda: self.move_group(-1))
        self.button(nav, _("Дальше ➡"), lambda: self.move_group(1), TEAL)
        if developer_mode():
            self.button(nav, _("Обновить отчёт"), self.save_dup_report)
        self.button(nav, _("К шагу 3 ➔"), lambda: self.goto_step(3), GREEN, side="right")

    def move_group(self, delta):
        self.dup_idx = (self.dup_idx + delta) % max(1, len(self.dup_groups))
        self.render_group()

    def delete_member(self, m):
        try:
            dst = move_file(m["path"], self.root_path / TRASH_DIR)
        except Exception as e:
            log.warning("Не удалось перенести %s: %s", m["path"], e)
            messagebox.showerror(_("Ошибка"), _("Не удалось перенести файл:\n{0}").format(e))
            return
        self.db.delete_files([str(m["path"])])
        self.db.log_action("move_deleted", str(m["path"]), str(dst))
        log.info("Перенесён в deleted: %s -> %s", m["path"], dst)
        self.dup_groups[self.dup_idx]["members"].remove(m)
        self.render_group()

    def save_dup_report(self):
        p = write_duplicates_report(self.svc_dir, self.dup_groups)
        messagebox.showinfo(_("Отчёт"), _("Сохранено:\n{0}").format(p))
