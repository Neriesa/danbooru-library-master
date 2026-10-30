# -*- coding: utf-8 -*-
"""Шаг 5: докачка Favorites."""

import tkinter as tk
from tkinter import messagebox


from .actions import migrate_legacy_found, sync_favorites
from .config import get_credentials
from .constants import GENERAL_DIR, LEGACY_DIR, OTHER_DIR
from .net import STOP
from .theme import BG, FG, MUTED, RED
from .i18n import _


class Step5Mixin:
    # ---------- шаг 5 ----------
    def render_step_5(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=_("Докачка недостающих файлов из Избранного"), font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=6)
        tk.Label(f, text=_("Скачиваются только те посты Избранного, которых нет в вашей папке (сверка по MD5 и ID).\n"
                         "Новые файлы попадают в general/ (рейтинг general) и other/ (остальные) как <id>.<расширение>. "
                         "Ваши файлы не затрагиваются."), fg=MUTED, bg=BG, font=("Arial", 10), justify="center").pack()
        opts = tk.Frame(f, bg=BG)
        opts.pack(pady=4)
        self.var_full5 = tk.BooleanVar(value=False)
        self.var_retry5 = tk.BooleanVar(value=False)
        self.check(opts, self.var_full5, _("Полностью перечитать список Избранного (медленнее)"))
        self.check(opts, self.var_retry5, _("Повторить ранее неудавшиеся / недоступные посты"))
        btns = tk.Frame(f, bg=BG)
        btns.pack(pady=6)
        self.btn_start5 = self.button(btns, _("Синхронизировать"), self.start_step5, "#009688", bold=True)
        self.button(btns, _("Остановить"), STOP.set, RED)
        if (self.root_path / LEGACY_DIR).is_dir() or self.db.undo_candidates("move_legacy"):
            btns2 = tk.Frame(f, bg=BG)
            btns2.pack(pady=2)
            self.button(btns2, _("Перенести старую папку found/ в general и other"), self.action_migrate_legacy)
            self.button(btns2, _("Отменить этот перенос"), lambda: self.action_undo("move_legacy"))
        self.make_progress_widgets(f)

    def action_migrate_legacy(self):
        if self.busy:
            return
        if not (self.root_path / LEGACY_DIR).is_dir():
            messagebox.showinfo(_("Нечего переносить"), _("Папки {0}/ нет.").format(LEGACY_DIR))
            return
        if not messagebox.askyesno(
                _("Перенос старой структуры"),
                _("Файлы из {0}/18+ и {1}/Others будут перенесены в {2}/ и {3}/ по рейтингу из базы. Перенос можно отменить. Продолжить?").format(LEGACY_DIR, LEGACY_DIR, GENERAL_DIR, OTHER_DIR)):
            return

        def work():
            migrate_legacy_found(self.db, self.root_path, self.say, self.progress)

        self.start_worker(work, lambda st: self.progress(1, 1, _("Перенос завершён") if st == "ok" else _("Остановлено или ошибка")))

    def start_step5(self):
        if self.busy:
            return
        user, _key = get_credentials()
        full, retry = self.var_full5.get(), self.var_retry5.get()
        self.btn_start5.config(state="disabled")

        def work():
            sync_favorites(self.db, self.root_path, user, full, retry, self.say, self.progress)

        def done(status):
            self.btn_start5.config(state="normal")
            self.progress(1, 1, {"ok": _("Синхронизация завершена"), "cancelled": _("Остановлено"),
                                 "error": _("Ошибка (см. журнал)")}[status])

        self.start_worker(work, done)
