# -*- coding: utf-8 -*-
"""Шаг 1: выбор папки, вход, просмотр, лента."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


from .bridges import BrowseServices, ViewerBridge
from . import app_paths
from .account import describe
from .config import CONFIG, developer_mode, get_credentials
from .dialogs import AboutDialog, ask_credentials
from .files import open_in_system
from .theme import BG, FG, GREEN, MUTED, TEAL
from .i18n import _


class Step1Mixin:
    # ---------- шаг 1 ----------
    def render_step_1(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(expand=True)
        tk.Label(f, text=_("Мастер библиотеки Danbooru"), font=("Arial", 18, "bold"), fg=FG, bg=BG).pack(pady=8)
        tk.Label(f, text=_("Выберите папку с вашей коллекцией (подпапки сканируются тоже).\n"
                         "Ваши файлы не перемещаются, пока вы сами не нажмёте соответствующую кнопку.\n"
                         "В вашей папке создаются только general/, other/ и deleted/.\n"
                         "База и отчёты хранятся отдельно, чтобы не мозолить глаза."),
                 fg=MUTED, bg=BG, justify="center", font=("Arial", 10)).pack(pady=10)
        tk.Button(f, text=_("ВЫБРАТЬ ПАПКУ"), command=self.action_select_dir, bg=GREEN, fg="white",
                  font=("Arial", 11, "bold"), padx=20, pady=10, relief="flat").pack(pady=15)
        self.lbl_path = tk.Label(f, text=str(self.root_path) if self.root_path else _("Папка не выбрана"),
                                 fg="#81c784" if self.root_path else "#ff5252", bg=BG, font=("Arial", 10, "italic"))
        self.lbl_path.pack()
        self.lbl_svc = tk.Label(f, text=_("Служебные файлы: {0}").format(self.svc_dir) if self.svc_dir else "",
                                fg=MUTED, bg=BG, font=("Arial", 9))
        if developer_mode():
            self.lbl_svc.pack(pady=(6, 0))
        row = tk.Frame(f, bg=BG)
        row.pack(pady=6)
        if developer_mode():
            self.button(row, _("Открыть папку служебных файлов"), self.open_service_dir)
        self.button(row, _("Сменить логин / API-ключ"), self.action_change_credentials)
        self.button(row, _("Случайный просмотр"), self.open_viewer, TEAL)
        self.button(row, _("Обзор рекомендаций"), self.open_browse, GREEN)
        self.button(row, _("О программе"), self.open_about)
        self.lbl_account = tk.Label(f, text=describe(CONFIG.get("account")), fg=MUTED, bg=BG, font=("Arial", 9))
        self.lbl_account.pack()
        tk.Button(f, text=_("Далее ➔"), command=lambda: self.goto_step(2), bg="#1de9b6", fg="black",
                  relief="flat", font=("Arial", 10, "bold"), padx=14, pady=4).pack(pady=25)

    def action_select_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.set_root(Path(d))
            self.lbl_path.config(text=str(self.root_path), fg="#81c784")
            self.lbl_svc.config(text=_("Служебные файлы: {0}").format(self.svc_dir))

    def open_viewer(self):
        from . import random_viewer
        random_viewer.Viewer(tk.Toplevel(self.root), self.root_path, ViewerBridge())

    def open_browse(self):
        user, key = get_credentials()
        if not (user and key):
            messagebox.showinfo(_("Нужен вход"), _("Для обзора нужны логин и API-ключ: нажмите «Сменить логин / API-ключ»."))
            return
        from . import browse
        browse.BrowseWindow(tk.Toplevel(self.root), BrowseServices(self.db, self))

    def action_change_credentials(self):
        if ask_credentials(self.root, first_run=False, on_restart=self.restart_for_language):
            self.update_account_label()
            messagebox.showinfo(_("Готово"), _("Логин и ключ сохранены."))

    def open_about(self):
        AboutDialog(self.root, self.svc_dir or app_paths.data_base(),
                    on_open_data=lambda: open_in_system(self.svc_dir or app_paths.data_base()),
                    on_restart=self.restart_for_language)

    def open_service_dir(self):
        if self.svc_dir:
            open_in_system(self.svc_dir)
        else:
            messagebox.showinfo(_("Папка не выбрана"), _("Сначала выберите рабочую папку."))
