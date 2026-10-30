# -*- coding: utf-8 -*-
"""Диалоги: первый вход / смена ключа, «О программе», предпросмотр перемещений."""

import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import i18n
from .account import AccountError, describe, refresh_account, store_account, verify_credentials
from .config import CONFIG, developer_mode, get_credentials, load_api_key, save_config, set_developer_mode, store_api_key
from .constants import APP_VERSION, OTHER_DIR
from .net import configure_session
from .theme import BG, BG2, FG, GREEN, GREY, MUTED, RED
from .i18n import _

API_HELP_URL = "https://danbooru.donmai.us/wiki_pages/help:api"
PROFILE_URL = "https://danbooru.donmai.us/profile"

DISCLAIMER = (_("Личный экспериментальный проект, написанный для себя и выложенный как есть: без гарантий и обещаний поддержки. "
              "Программа перемещает файлы, поэтому сначала попробуйте её на копии небольшой папки. "
              "Danbooru содержит материалы 18+. Проект неофициальный и с Danbooru не связан."))


def link(parent, text, url, bg=BG, size=10):
    lb = tk.Label(parent, text=text, fg="#64b5f6", bg=bg, cursor="hand2", font=("Arial", size, "underline"))
    lb.bind("<Button-1>", lambda e: webbrowser.open(url))
    return lb


def center_on(win, parent):
    win.update_idletasks()
    try:
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - win.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - win.winfo_height()) // 3)
        win.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass


def language_row(parent, bg=BG, on_changed=None):
    """Выбор языка. Смена сохраняется и перезапускает программу."""
    row = tk.Frame(parent, bg=bg)
    tk.Label(row, text="Язык / Language:", fg=MUTED, bg=bg).pack(side="left")
    var = tk.StringVar(value=i18n.LANGS[i18n.language()])
    box = ttk.Combobox(row, textvariable=var, values=list(i18n.LANGS.values()), state="readonly", width=12)
    box.pack(side="left", padx=6)

    def changed(_e=None):
        code = next((c for c, name in i18n.LANGS.items() if name == var.get()), i18n.language())
        if code == i18n.language():
            return
        if messagebox.askyesno("Language / Язык",
                               "Чтобы применить язык, программа перезапустится.\nThe program will restart to apply the language.",
                               parent=parent):
            i18n.save_language(code)
            if on_changed:
                on_changed(code)
        else:
            var.set(i18n.LANGS[i18n.language()])

    box.bind("<<ComboboxSelected>>", changed)
    return row


class ToggleSwitch(tk.Canvas):
    """Переключатель вкл/выкл: клик мышью, Пробел или Enter."""

    W, H = 44, 22

    def __init__(self, parent, value=False, command=None, bg=BG):
        super().__init__(parent, width=self.W, height=self.H, bg=bg, cursor="hand2", takefocus=1,
                         highlightthickness=1, highlightbackground=bg, highlightcolor=FG)
        self.value, self.command = bool(value), command
        for seq in ("<Button-1>", "<space>", "<Return>"):
            self.bind(seq, self.toggle)
        self.draw()

    def draw(self):
        self.delete("all")
        w, h, color = self.W, self.H, GREEN if self.value else GREY
        self.create_oval(1, 1, h - 1, h - 1, fill=color, outline=color)
        self.create_oval(w - h + 1, 1, w - 1, h - 1, fill=color, outline=color)
        self.create_rectangle(h // 2, 1, w - h // 2, h - 1, fill=color, outline=color)
        x = w - h + 3 if self.value else 3
        self.create_oval(x, 3, x + h - 6, h - 3, fill="white", outline="white")

    def toggle(self, _e=None):
        self.value = not self.value
        self.draw()
        if self.command:
            self.command(self.value)


class CredentialsDialog:
    """Первый запуск и смена логина / ключа: подсказки, где взять ключ, проверка и сведения об аккаунте."""

    def __init__(self, parent, first_run=False, on_restart=None):
        self.first_run = first_run
        self.saved = False
        self.acc = None
        self.checked_ok = False
        self.q = queue.Queue()
        self.win = tk.Toplevel(parent)
        self.win.configure(bg=BG)
        self.win.title(_("Добро пожаловать") if first_run else _("Логин и API-ключ"))
        if not first_run:                      # на первом запуске главное окно скрыто: transient спрятал бы и диалог
            self.win.transient(parent)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.cancel)
        w = self.win
        pad = {"padx": 22}

        if first_run:
            tk.Label(w, text="Danbooru Library Master", font=("Arial", 16, "bold"), fg=FG, bg=BG).pack(pady=(16, 2), **pad)
            tk.Label(w, text=_("Порядок в вашей коллекции картинок и видео с Danbooru"), fg=MUTED, bg=BG).pack(**pad)
            tk.Label(w, text=DISCLAIMER, fg="#ffb74d", bg=BG, wraplength=560, justify="left",
                     font=("Arial", 9)).pack(pady=(10, 4), **pad)
        else:
            tk.Label(w, text=_("Логин и API-ключ"), font=("Arial", 14, "bold"), fg=FG, bg=BG).pack(pady=(16, 4), **pad)

        tk.Label(w, text=_("Как получить API-ключ"), font=("Arial", 11, "bold"), fg=FG, bg=BG, anchor="w").pack(
            fill="x", pady=(10, 2), **pad)
        steps = (_("1. Войдите на Danbooru под своей учётной записью (если её нет, зарегистрируйтесь).\n"
                 "2. Откройте свой профиль и найдите там раздел «API Keys» (ключи API) в настройках профиля.\n"
                 "3. Создайте новый ключ и отметьте права. Для просмотра, сверки и докачки достаточно прав на чтение. "
                 "Для кнопок «в Favorites» и «убрать из Favorites» нужны права на избранное (favorites).\n"
                 "4. Скопируйте ключ и вставьте его ниже. Ключ равноценен паролю: никому его не показывайте."))
        tk.Label(w, text=steps, fg=FG, bg=BG, wraplength=560, justify="left", anchor="w").pack(fill="x", **pad)
        lr = tk.Frame(w, bg=BG)
        lr.pack(fill="x", pady=(4, 0), **pad)
        link(lr, _("Официальная справка Danbooru по API (на английском)"), API_HELP_URL).pack(anchor="w")
        link(lr, _("Открыть мой профиль на Danbooru"), PROFILE_URL).pack(anchor="w")

        form = tk.Frame(w, bg=BG)
        form.pack(fill="x", pady=(12, 0), **pad)
        tk.Label(form, text=_("Логин:"), fg=FG, bg=BG, width=10, anchor="w").grid(row=0, column=0, pady=3)
        self.var_user = tk.StringVar(value=get_credentials()[0])
        tk.Entry(form, textvariable=self.var_user, width=34, bg="#222222", fg=FG, insertbackground=FG).grid(row=0, column=1, sticky="w")
        tk.Label(form, text=_("API-ключ:"), fg=FG, bg=BG, width=10, anchor="w").grid(row=1, column=0, pady=3)
        self.var_key = tk.StringVar()
        self.ent_key = tk.Entry(form, textvariable=self.var_key, width=34, show="*", bg="#222222", fg=FG, insertbackground=FG)
        self.ent_key.grid(row=1, column=1, sticky="w")
        self.var_show = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text=_("показать"), variable=self.var_show, command=self.toggle_show, bg=BG, fg=MUTED,
                       selectcolor=BG, activebackground=BG, activeforeground=FG).grid(row=1, column=2, padx=6)
        if not first_run:
            tk.Label(form, text=_("Ключ можно оставить пустым: тогда останется сохранённый."), fg=MUTED, bg=BG,
                     font=("Arial", 9)).grid(row=2, column=1, sticky="w")

        self.lbl_status = tk.Label(w, text="", fg=MUTED, bg=BG, wraplength=560, justify="left", anchor="w")
        self.lbl_status.pack(fill="x", pady=(10, 2), **pad)

        btns = tk.Frame(w, bg=BG)
        btns.pack(pady=(6, 6), **pad)
        self.btn_check = tk.Button(btns, text=_("Проверить ключ"), command=self.start_check, bg="#009688", fg="white",
                                   relief="flat", padx=12, pady=5)
        self.btn_check.pack(side="left", padx=4)
        self.btn_save = tk.Button(btns, text=_("Сохранить и продолжить"), command=self.save, bg=GREEN, fg="white",
                                  relief="flat", padx=12, pady=5, state="disabled")
        self.btn_save.pack(side="left", padx=4)
        tk.Button(btns, text=_("Выйти") if first_run else _("Отмена"), command=self.cancel, bg=GREY, fg="white", relief="flat",
                  padx=12, pady=5).pack(side="left", padx=4)

        language_row(w, on_changed=on_restart).pack(pady=(2, 14))
        center_on(w, parent)
        w.grab_set()
        self.ent_key.focus_set()
        self.win.after(100, self.poll)

    def toggle_show(self):
        self.ent_key.config(show="" if self.var_show.get() else "*")

    def _key(self, user):
        return self.var_key.get().strip() or load_api_key(user)

    def start_check(self):
        user = self.var_user.get().strip()
        key = self._key(user)
        if not user or not key:
            self.set_status(_("Введите логин и API-ключ."), RED)
            return
        self.btn_check.config(state="disabled")
        self.set_status(_("Проверяю вход…"), MUTED)

        def work():
            try:
                self.q.put(("ok", verify_credentials(user, key)))
            except AccountError as e:
                self.q.put(("err", e))
            except Exception as e:
                self.q.put(("err", AccountError(str(e), "other")))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                self.btn_check.config(state="normal")
                if kind == "ok":
                    self.show_account(payload)
                else:
                    self.show_error(payload)
        except queue.Empty:
            pass
        if self.win.winfo_exists():
            self.win.after(100, self.poll)

    def show_account(self, acc):
        self.acc, self.checked_ok = acc, True
        if acc["tier"] == "gold":
            tip = _("У вас Gold или выше: доступны все режимы, запросы до {0} тегов.").format(acc['tag_limit'])
        elif acc["tier"] == "free":
            tip = (_("У вас бесплатный аккаунт (запросы до {0} тегов). Сверка с сайтом, дубликаты, докачка и просмотр работают полностью. В ленте «Обзор» часть режимов упрощена: сортировка по очкам выполняется на вашем компьютере.").format(acc['tag_limit']))
        else:
            tip = _("Уровень аккаунта определить не удалось: лента будет работать в осторожном режиме.")
        self.set_status(_("✓ Вход выполнен: {0} ({1}).\n{2}").format(acc['name'], acc['level_string'], tip), "#81c784")
        self.btn_save.config(state="normal", text=_("Сохранить и продолжить"))

    def show_error(self, err):
        if err.kind == "network":
            self.set_status(_("{0}\nМожно сохранить данные без проверки и проверить позже.").format(err), "#ffb74d")
            self.btn_save.config(state="normal", text=_("Сохранить без проверки"))
        elif err.kind == "auth":
            self.set_status(_("{0}. Проверьте логин (без пробелов в начале и конце) и скопируйте ключ целиком.").format(err), RED)
            self.btn_save.config(state="disabled")
        else:
            self.set_status(str(err), RED)
            self.btn_save.config(state="disabled")

    def set_status(self, text, color):
        self.lbl_status.config(text=text, fg=color)

    def save(self):
        user = self.var_user.get().strip()
        key = self._key(user)
        if not user or not key:
            return
        CONFIG["username"] = user
        store_api_key(user, key)
        if self.acc:
            store_account(self.acc)
        save_config()
        configure_session(user, key)
        self.saved = True
        self.win.destroy()

    def cancel(self):
        self.win.destroy()


def ask_credentials(parent, first_run=False, on_restart=None) -> bool:
    dlg = CredentialsDialog(parent, first_run, on_restart)
    parent.wait_window(dlg.win)
    return dlg.saved


class AboutDialog:
    def __init__(self, parent, data_dir, on_open_data=None, on_restart=None):
        w = self.win = tk.Toplevel(parent)
        w.configure(bg=BG)
        w.title(_("О программе"))
        w.transient(parent)
        w.resizable(False, False)
        tk.Label(w, text="Danbooru Library Master", font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=(16, 0), padx=24)
        tk.Label(w, text=_("Версия {0}").format(APP_VERSION), fg=MUTED, bg=BG).pack()
        tk.Label(w, text=DISCLAIMER, fg="#ffb74d", bg=BG, wraplength=480, justify="left").pack(pady=10, padx=24)
        self.lbl_acc = tk.Label(w, text=describe(CONFIG.get("account")), fg=FG, bg=BG, wraplength=480, justify="left")
        self.lbl_acc.pack(padx=24)
        tk.Button(w, text=_("Обновить сведения об аккаунте"), command=self.refresh, bg=GREY, fg="white", relief="flat",
                  padx=10, pady=4).pack(pady=10)

        dev = tk.Frame(w, bg=BG)
        dev.pack(fill="x", padx=24)
        tk.Label(dev, text=_("Настройки разработчика"), fg=FG, bg=BG, font=("Arial", 10, "bold")).pack(side="left")
        self.switch = ToggleSwitch(dev, developer_mode(), self.set_dev)
        self.switch.pack(side="right")
        self.lbl_dev_state = tk.Label(dev, fg=MUTED, bg=BG)
        self.lbl_dev_state.pack(side="right", padx=8)
        tk.Label(w, text=_("Счётчики запросов и трафика, HTML-отчёты, служебные папки и кнопки. Обычному пользователю не нужны."),
                 fg=MUTED, bg=BG, wraplength=480, justify="left", font=("Arial", 9)).pack(fill="x", padx=24)
        self.dev_holder = tk.Frame(w, bg=BG)          # держит место в окне, пока блок разработчика скрыт
        self.dev_holder.pack(fill="x", padx=24)
        self.dev_box = tk.Frame(self.dev_holder, bg=BG)
        tk.Label(self.dev_box, text=_("Папка данных: {0}").format(data_dir), fg=MUTED, bg=BG, wraplength=480, justify="left",
                 font=("Arial", 9)).pack(anchor="w", pady=(8, 4))
        if on_open_data:
            tk.Button(self.dev_box, text=_("Открыть папку данных"), command=on_open_data, bg=GREY, fg="white", relief="flat",
                      padx=10, pady=4).pack(anchor="w", pady=(0, 4))
        link(self.dev_box, _("Справка Danbooru по API"), API_HELP_URL).pack(anchor="w")
        self.show_dev()

        language_row(w, on_changed=on_restart).pack(pady=10)
        tk.Button(w, text=_("Закрыть"), command=w.destroy, bg=BG2, fg=FG, relief="flat", padx=14, pady=4).pack(pady=(0, 14))
        center_on(w, parent)

    def set_dev(self, on):
        set_developer_mode(on)
        self.show_dev()

    def show_dev(self):
        on = developer_mode()
        self.lbl_dev_state.config(text=_("Вкл") if on else _("Выкл"), fg=GREEN if on else MUTED)
        if on:
            self.dev_box.pack(fill="x")
        else:
            self.dev_box.pack_forget()

    def refresh(self):
        user, key = get_credentials()
        if not (user and key):
            return
        self.lbl_acc.config(text=_("Проверяю…"))

        def work():
            acc = refresh_account(user, key)
            self.win.after(0, lambda: self.lbl_acc.config(text=describe(acc)))

        threading.Thread(target=work, daemon=True).start()


class MovePreview:
    """Пробный режим: список того, что будет перенесено в other/. Файлы не меняются, пока вы не подтвердите."""

    def __init__(self, parent, plan, title=None):
        self.confirmed = False
        w = self.win = tk.Toplevel(parent)
        w.configure(bg=BG)
        w.title(title or _("Что будет перенесено"))
        w.transient(parent)
        w.geometry("760x520")
        by_cat = {}
        for p in plan:
            by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
        from .constants import CATEGORY_LABELS
        summary = "; ".join(f"{CATEGORY_LABELS.get(c, c)}: {n}" for c, n in by_cat.items())
        tk.Label(w, text=_("Файлов будет перенесено в {0}/: {1}").format(OTHER_DIR, len(plan)), font=("Arial", 13, "bold"), fg=FG, bg=BG).pack(
            pady=(12, 0), padx=16, anchor="w")
        tk.Label(w, text=summary or _("Нечего переносить"), fg=MUTED, bg=BG, wraplength=720, justify="left").pack(padx=16, anchor="w")
        tk.Label(w, text=_("К имени добавляется пометка. Если такое имя уже занято, программа подберёт другое. "
                         "Всё можно вернуть кнопкой «Вернуть из other/» на шаге 4."), fg=MUTED, bg=BG, wraplength=720,
                 justify="left", font=("Arial", 9)).pack(padx=16, pady=(2, 6), anchor="w")
        frame = tk.Frame(w, bg=BG)
        frame.pack(fill="both", expand=True, padx=16)
        cols = ("src", "dst")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        tree.heading("src", text=_("Файл сейчас"))
        tree.heading("dst", text=_("Новое имя в other/"))
        tree.column("src", width=380)
        tree.column("dst", width=320)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for p in plan:
            tree.insert("", "end", values=(p["src"], p["new_name"] + (_("  (имя занято)") if p["clash"] else "")))
        self.plan = plan
        row = tk.Frame(w, bg=BG)
        row.pack(pady=10)
        tk.Button(row, text=_("Сохранить список в файл"), command=self.save_list, bg=GREY, fg="white", relief="flat", padx=10,
                  pady=5).pack(side="left", padx=4)
        state = "normal" if plan else "disabled"
        tk.Button(row, text=_("Перенести"), command=self.confirm, bg=GREEN, fg="white", relief="flat", padx=14, pady=5,
                  state=state).pack(side="left", padx=4)
        tk.Button(row, text=_("Не переносить"), command=w.destroy, bg=GREY, fg="white", relief="flat", padx=14, pady=5).pack(
            side="left", padx=4)
        center_on(w, parent)
        w.grab_set()

    def save_list(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".txt", initialfile="planned_moves.txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            for p in self.plan:
                fh.write(f"{p['src']}\t->\t{OTHER_DIR}/{p['new_name']}\n")

    def confirm(self):
        self.confirmed = True
        self.win.destroy()


def preview_moves(parent, plan, title=None) -> bool:
    dlg = MovePreview(parent, plan, title)
    parent.wait_window(dlg.win)
    return dlg.confirmed
