# -*- coding: utf-8 -*-
"""Главное окно программы: каркас и вспомогательные функции. Шаги лежат в ui_step*.py."""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


from . import i18n
from .account import describe, refresh_account
from .config import CONFIG, developer_mode, get_credentials, log, save_config
from .dialogs import ask_credentials
from .constants import APP_VERSION, LOG_PATH
from .db import LibraryDB
from .files import migrate_service_files, service_dir
from .net import Cancelled, STOP
from .theme import BG, BG2, FG, GREEN, GREY, MUTED
from .ui_step1 import Step1Mixin
from .ui_step2 import Step2Mixin
from .ui_step3 import Step3Mixin
from .ui_step4 import Step4Mixin
from .ui_step5 import Step5Mixin
from .ui_step6 import Step6Mixin
from .i18n import _


class App(Step1Mixin, Step2Mixin, Step3Mixin, Step4Mixin, Step5Mixin, Step6Mixin):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Danbooru Library Master {APP_VERSION}")
        self.root.geometry("1220x820")
        self.root.configure(bg=BG)

        self.root_path = None
        self.db = None
        self.svc_dir = None
        self.busy = False
        self.step = 1
        self.dev_shown = developer_mode()
        self.ui_queue = queue.Queue()
        self.pb = None
        self.lbl_detail = None
        self.log_box = None
        self._last_progress = 0.0
        self.photos = []
        self.dup_groups = []
        self.dup_idx = 0
        self.results = []
        self.view_rows = []
        self.tree = None

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TProgressbar", thickness=15, background=GREEN)
        self.style.configure("Treeview", background="#222222", fieldbackground="#222222",
                             foreground=FG, rowheight=22, borderwidth=0)
        self.style.configure("Treeview.Heading", background=BG2, foreground=FG)
        self.style.map("Treeview", background=[("selected", "#00695c")])

        self.step_bar = tk.Frame(root, bg=BG2, height=50)
        self.step_bar.pack(fill="x", side="top")
        self.step_buttons = []
        names = [_("1. Папка"), _("2. Дубликаты"), _("3. Сверка с Danbooru"), _("4. Результаты"), _("5. Докачка"), _("6. Мои теги")]
        for i, text in enumerate(names, 1):
            b = tk.Button(self.step_bar, text=text, bg=BG2, fg="#888888", relief="flat",
                          font=("Arial", 10, "bold"), command=lambda n=i: self.goto_step(n))
            b.pack(side="left", expand=True, fill="x", ipady=8)
            self.step_buttons.append(b)

        self.main = tk.Frame(root, bg=BG)
        self.main.pack(fill="both", expand=True, padx=20, pady=15)

        last = CONFIG.get("last_folder")
        if last and Path(last).is_dir():
            self.set_root(Path(last))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self.poll_queue)
        self.show_step(1)
        threading.Thread(target=self._refresh_account, daemon=True).start()

    # ---------- служебное ----------
    def _refresh_account(self):
        """При запуске узнаём уровень аккаунта (один лёгкий запрос) и обновляем строку на первом шаге."""
        user, key = get_credentials()
        if not (user and key):
            return
        refresh_account(user, key)
        self.ui(self.update_account_label)

    def update_account_label(self):
        lbl = getattr(self, "lbl_account", None)
        try:
            if lbl is not None and lbl.winfo_exists():
                lbl.config(text=describe(CONFIG.get("account")))
        except tk.TclError:
            pass

    def restart_for_language(self, code):
        if self.busy:
            messagebox.showinfo(_("Подождите"), _("Дождитесь окончания текущей работы и повторите смену языка."))
            return
        restart_with_language(self.root)

    def ui(self, fn, *args):
        """Безопасно вызвать функцию интерфейса из любого потока."""
        self.ui_queue.put((fn, args))

    def apply_developer_mode(self):
        """Переключатель в «О программе»: перерисовываем шаг. Шаг 3 и 5 не трогаем, там журнал работы."""
        if self.step == 2:
            if self.dup_groups:
                self.render_group()                # show_step убрал бы показанную группу
        elif self.step in (1, 4, 6):
            self.show_step(self.step)

    def poll_queue(self):
        if self.dev_shown != developer_mode() and not self.busy:     # во время работы подождёт её окончания
            self.dev_shown = developer_mode()
            self.ui(self.apply_developer_mode)
        try:
            while True:
                fn, args = self.ui_queue.get_nowait()
                try:
                    fn(*args)
                except tk.TclError:
                    pass  # виджет уже уничтожен при смене шага
        except queue.Empty:
            pass
        self.root.after(50, self.poll_queue)

    def say(self, text, level="info"):
        getattr(log, "warning" if level in ("warn", "error") else "info")(text)
        self.ui(self._append_log, text)

    def _append_log(self, text):
        if self.log_box is None:
            return
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def progress(self, done, total, text):
        now = time.monotonic()
        if now - self._last_progress < 0.1 and done != total:
            return
        self._last_progress = now
        self.ui(self._apply_progress, done, total, text)

    def _apply_progress(self, done, total, text):
        if self.pb is not None:
            if total:
                self.pb.config(mode="determinate", maximum=total, value=done)
            else:
                self.pb.config(mode="indeterminate")
                self.pb.step(2)
        if self.lbl_detail is not None:
            self.lbl_detail.config(text=text)

    def start_worker(self, work, on_done):
        STOP.clear()
        self.busy = True

        def runner():
            status = "ok"
            try:
                work()
            except Cancelled:
                status = "cancelled"
                self.say(_("Остановлено пользователем."))
            except Exception as e:
                status = "error"
                log.exception("Ошибка в рабочем потоке")
                self.say(_("ОШИБКА: {0}").format(e), "error")
            finally:
                self.busy = False
                self.ui(on_done, status)

        threading.Thread(target=runner, daemon=True).start()

    def on_close(self):
        STOP.set()
        if self.db:
            self.db.close()
        self.root.destroy()

    def set_root(self, path: Path):
        if self.db:
            self.db.close()
        self.root_path = path
        self.svc_dir = service_dir(path)
        try:
            migrate_service_files(path, self.svc_dir, log.warning)
        except Exception as e:
            log.exception("Не удалось перенести служебные файлы")
            messagebox.showerror(_("Служебные файлы"), _("Не удалось перенести базу в {0}:\n{1}\n\nДанные не потеряны: старая база осталась в рабочей папке.").format(self.svc_dir, e))
            self.svc_dir = path           # работаем со старым расположением
        self.db = LibraryDB(self.svc_dir / "library.db")
        CONFIG["last_folder"] = str(path)
        save_config()

    def goto_step(self, n):
        if self.busy:
            self.root.bell()
            return
        if n > 1 and not self.db:
            messagebox.showinfo(_("Папка не выбрана"), _("Сначала выберите рабочую папку (шаг 1)."))
            return
        self.show_step(n)

    def show_step(self, n):
        self.step = n
        for i, b in enumerate(self.step_buttons, 1):
            b.config(fg=GREEN if i == n else "#888888")
        for w in self.main.winfo_children():
            w.destroy()
        self.pb = self.lbl_detail = self.log_box = self.tree = None
        [None, self.render_step_1, self.render_step_2, self.render_step_3,
         self.render_step_4, self.render_step_5, self.render_step_6][n]()

    def make_progress_widgets(self, parent, log_height=14):
        self.pb = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.pb.pack(fill="x", pady=8)
        self.lbl_detail = tk.Label(parent, text="", bg=BG, fg=MUTED, font=("Arial", 10))
        self.lbl_detail.pack()
        self.log_box = ScrolledText(parent, height=log_height, bg="#111111", fg="#cfd8dc",
                                    insertbackground="white", relief="flat", state="disabled")
        self.log_box.pack(fill="both", expand=True, pady=8)

    @staticmethod
    def check(parent, var, text):
        tk.Checkbutton(parent, text=text, variable=var, bg=BG, fg=FG, selectcolor=BG2,
                       activebackground=BG, activeforeground=FG).pack(anchor="w")

    @staticmethod
    def button(parent, text, command, color=GREY, side="left", bold=False, **kw):
        b = tk.Button(parent, text=text, command=command, bg=color, fg="white", relief="flat",
                      font=("Arial", 10, "bold" if bold else "normal"), padx=12, pady=5, **kw)
        b.pack(side=side, padx=4)
        return b


def restart_with_language(root: tk.Tk):
    """Язык уже сохранён: запускаем программу заново и закрываем это окно."""
    i18n.restart_program()
    root.destroy()


def ensure_credentials(root: tk.Tk) -> bool:
    """Первый запуск: окно с инструкцией, проверкой ключа и сведениями об аккаунте."""
    user, key = get_credentials()
    if user and key:
        return True
    root.withdraw()
    try:
        return ask_credentials(root, first_run=True, on_restart=lambda code: restart_with_language(root))
    except tk.TclError:                    # окно закрыто перезапуском
        return False
    finally:
        try:
            root.deiconify()
        except tk.TclError:
            pass


def report_tk_error(exc, val, tb):
    """Ошибки в обработчиках кнопок: в журнал и в окно, программа продолжает работать."""
    log.error("Необработанная ошибка", exc_info=(exc, val, tb))
    try:
        messagebox.showerror(_("Ошибка"), _("{0}\n\nПодробности записаны в журнал:\n{1}").format(val, LOG_PATH))
    except Exception:
        pass
