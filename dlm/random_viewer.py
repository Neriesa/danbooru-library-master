# -*- coding: utf-8 -*-
"""
Случайный просмотр: показывает картинки, анимации (GIF, WebP, APNG) и видео из папки в случайном
порядке. Файлы НЕ переименовываются, поэтому ID постов в именах остаются на месте.

Запуск:
    ярлык «Случайный просмотр» (DanbooruLibraryMaster.exe --viewer) или кнопка на первом шаге программы
    python random_viewer.py            - окно, папка выбирается кнопкой (или берётся последняя рабочая папка)
    python random_viewer.py ПАПКА      - сразу открыть папку

Клавиши (работают и в русской раскладке):
    →  Пробел  ↓   следующая          ←  ↑   предыдущая
    R (К)          перемешать заново   S (Ы)  автопоказ вкл/выкл
    F (А) / F11    полный экран        Esc    выйти из полного экрана
    V (М)          пауза / продолжить анимацию или видео (они играют в окне по кругу, видео без звука)
    O (Щ)          открыть файл в программе по умолчанию (для видео - в плеере со звуком)
    P (З)          открыть пост на Danbooru        C (С)  скопировать ID/имя файла
    Delete         убрать файл: снять с Favorites на сайте (если стоит) и перенести в deleted/ (с вопросом)
Колесо мыши листает. Каждый файл показывается один раз за круг, потом порядок перемешивается заново.

Кнопки «Открыть пост» и «Удалить» работают, когда папка известна программе (шаги 2-3 основной программы):
ID берётся из имени файла (<id>.jpg, siteDeleted_<id>.jpg) или из базы программы.
"""

import json
import os
import queue
import random
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from . import app_paths
from .config import log
from .i18n import _

try:
    import cv2
except ImportError:  # без opencv видео просто не показываются
    cv2 = None

BASE_URL = "https://danbooru.donmai.us"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
ANIM_CANDIDATES = {".gif", ".webp", ".png"}   # здесь может быть анимация
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}
SKIP_DIRS = {"deleted"}
NOTFOUND_PREFIX = "notFound_"
SITE_DELETED_PREFIX = "siteDeleted_"
CONFIG_PATH = app_paths.config_path()

FILTER_ALL = _("Все")
FILTER_GENERAL = _("Только general")
FILTER_OTHER = _("Только other")
FILTER_NO_NF = _("Без пометок notFound_/siteDeleted_")
FILTERS = [FILTER_ALL, FILTER_GENERAL, FILTER_OTHER, FILTER_NO_NF]

BG, FG, MUTED = "#111111", "#ffffff", "#9e9e9e"
BAR = "#222222"
MARKS = (NOTFOUND_PREFIX, SITE_DELETED_PREFIX)

# Клавиши: по имени клавиши (стрелки, пробел) и по набранному символу. Русские буквы стоят на тех же
# физических клавишах, поэтому работают при любой раскладке.
KEY_ACTIONS = {
    "Right": "next", "Down": "next", "space": "next", "Next": "next",
    "Left": "prev", "Up": "prev", "Prior": "prev",
    "Escape": "escape", "Delete": "remove", "F11": "fullscreen",
}
CHAR_ACTIONS = {}
for _action, _chars in {
    "reshuffle": "r\u043a",      # r / к
    "slideshow": "s\u044b",      # s / ы
    "fullscreen": "f\u0430",     # f / а
    "open_file": "o\u0449",      # o / щ
    "toggle_play": "v\u043c",    # v / м
    "open_post": "p\u0437",      # p / з
    "copy_id": "c\u0441",        # c / с
}.items():
    for _ch in _chars:
        CHAR_ACTIONS[_ch] = _action
TEXT_WIDGETS = {"Spinbox", "TSpinbox", "Entry", "TEntry", "TCombobox", "Text"}


def scan_folder(root: Path, with_video: bool):
    exts = IMAGE_EXT | (VIDEO_EXT if (with_video and cv2 is not None) else set())
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if Path(dirpath) == root:
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for n in filenames:
            if Path(n).suffix.lower() in exts:
                out.append(Path(dirpath) / n)
    return out


def apply_filter(files, root: Path, flt: str):
    if flt == FILTER_ALL:
        return list(files)
    out = []
    for p in files:
        try:
            top = p.relative_to(root).parts[0].lower()
        except (ValueError, IndexError):
            top = ""
        if flt == FILTER_GENERAL and top == "general":
            out.append(p)
        elif flt == FILTER_OTHER and top == "other":
            out.append(p)
        elif flt == FILTER_NO_NF and not p.name.startswith(MARKS):
            out.append(p)
    return out


def post_id_from_name(path: Path):
    """Файлы Danbooru Library Master называются <id>.<расширение>, а файлы с удалённых постов - siteDeleted_<id>."""
    stem = path.stem
    if stem.startswith(SITE_DELETED_PREFIX):
        stem = stem[len(SITE_DELETED_PREFIX):]
    return int(stem) if stem.isdigit() else None


def open_in_system(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        log.warning("Не удалось открыть %s: %s", path, e)


def load_frame(path: Path):
    """Статичная картинка для показа. Бросает исключение, если файл не открылся."""
    img = Image.open(path)
    img.load()
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img.convert("RGB")


# ============================ ПРОИГРЫВАТЕЛИ ============================

class VideoPlayer:
    """Видео через OpenCV (без звука)."""

    def __init__(self, path: Path):
        self.path = path
        self.cap = cv2.VideoCapture(str(path))
        ok, frame = self.cap.read()
        if not ok:
            self.cap.release()
            raise ValueError(_("встроенный плеер не смог прочитать это видео; "
                             "нажмите O, чтобы открыть его в системном плеере"))
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 0
        self.delay = int(1000 / fps) if 1 <= fps <= 60 else 40
        frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        dur = _("{0:.1f} с, ").format(frames * self.delay / 1000) if frames else ""
        self.description = _("    видео {0}без звука (O - в плеере)").format(dur)
        self.first = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    def read(self):
        """Следующий кадр: (PIL-изображение, задержка в мс) или None, если ролик закончился."""
        ok, frame = self.cap.read()
        if not ok:
            return None
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), self.delay

    def rewind(self):
        if not self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0):
            self.cap.release()
            self.cap = cv2.VideoCapture(str(self.path))

    def close(self):
        self.cap.release()


class AnimPlayer:
    """Анимированные GIF / WebP / APNG: кадры декодируются по одному, в память целиком не грузятся."""

    def __init__(self, img: Image.Image):
        self.img = img
        self.n = img.n_frames
        self.i = 0
        self.delay = 100
        self.description = _("    анимация, {0} кадров").format(self.n)
        self.first = self._frame(0)

    def _frame(self, i: int):
        self.img.seek(i)
        self.img.load()                              # у WebP длительность кадра появляется только после load()
        d = self.img.info.get("duration", 100) or 0
        self.delay = d if d >= 20 else 100          # 0-19 мс браузеры тоже читают как 100 мс
        im = self.img
        if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
            rgba = im.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (17, 17, 17, 255))   # прозрачное - на фоне окна
            return Image.alpha_composite(bg, rgba).convert("RGB")
        return im.convert("RGB")

    def read(self):
        self.i += 1
        if self.i >= self.n:
            return None
        frame = self._frame(self.i)
        return frame, self.delay

    def rewind(self):
        self.i = -1                                  # следующий read() вернёт кадр 0

    def close(self):
        try:
            self.img.close()
        except Exception:
            pass


def make_player(path: Path):
    """Возвращает проигрыватель для видео и анимаций, для обычных картинок - None."""
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return VideoPlayer(path)
    if ext in ANIM_CANDIDATES:
        img = Image.open(path)
        if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
            return AnimPlayer(img)
        img.close()
    return None


# ============================ ОКНО ============================

class Viewer:
    """
    bridge - необязательная связь с базой программы (ViewerBridge из danbooru_library_master):
    post_id_for(path), removal_info(path), remove(path), find_root(path).
    """

    def __init__(self, win: tk.Misc, folder: Path = None, bridge=None):
        self.win = win
        self.bridge = bridge
        self.root_path = None
        self.all_files = []
        self.order = []
        self.pos = 0
        self.photo = None
        self.current_img = None
        self.slideshow_job = None
        self.resize_job = None
        self.laps = 0
        self.player = None             # проигрыватель видео/анимации
        self.player_job = None
        self.paused = False
        self.loops = 0
        self.play_started = 0.0
        self.play_info = ""
        self.last_frame = None         # последний показанный кадр (для перерисовки при изменении размера окна)
        self.notice = ""               # короткое сообщение, показывается в строке состояния один раз
        self.pid_cache = {}
        self.removing = False
        self.is_full = False           # полноэкранный режим (состояние храним сами: системе доверять не всегда можно)
        self.alive = True
        self.q = queue.Queue()

        win.title(_("Случайный просмотр"))
        app_paths.set_window_icon(win)
        win.geometry("1100x800")
        win.configure(bg=BG)

        # --- верхняя панель настроек: ничего из этого не должно перехватывать клавиши (takefocus=0) ---
        self.bar = tk.Frame(win, bg=BAR)
        self.bar.pack(fill="x", side="top")
        self.make_button(self.bar, _("Папка…"), self.choose_folder).pack(side="left", padx=4, pady=4)
        self.lbl_folder = tk.Label(self.bar, text=_("Папка не выбрана"), bg=BAR, fg=MUTED)
        self.lbl_folder.pack(side="left", padx=6)
        self.make_button(self.bar, _("Перемешать (R)"), self.reshuffle).pack(side="right", padx=4)
        self.btn_slide = self.make_button(self.bar, _("Автопоказ (S)"), self.toggle_slideshow)
        self.btn_slide.pack(side="right", padx=4)
        self.spin = tk.Spinbox(self.bar, from_=1, to=120, width=4)
        self.spin.delete(0, "end")
        self.spin.insert(0, "4")
        self.spin.pack(side="right")
        self.spin.bind("<Return>", lambda e: self.focus_canvas())
        tk.Label(self.bar, text=_("сек:"), bg=BAR, fg=FG).pack(side="right")
        self.var_video = tk.BooleanVar(value=cv2 is not None)
        self.var_play = tk.BooleanVar(value=True)
        self.btn_play = self.make_button(self.bar, _("Пауза (V)"), self.toggle_play)
        self.btn_play.pack(side="right", padx=4)
        tk.Checkbutton(self.bar, text=_("играть анимации"), variable=self.var_play, bg=BAR, fg=FG, takefocus=0,
                       selectcolor=BAR, activebackground=BAR, activeforeground=FG,
                       command=self.focus_canvas).pack(side="right", padx=4)
        if cv2 is not None:
            tk.Checkbutton(self.bar, text=_("видео"), variable=self.var_video, bg=BAR, fg=FG, takefocus=0,
                           selectcolor=BAR, activebackground=BAR, activeforeground=FG,
                           command=self.reload).pack(side="right", padx=6)
        self.cmb = ttk.Combobox(self.bar, state="readonly", width=30, values=FILTERS, takefocus=0)
        self.cmb.set(FILTER_ALL)
        self.cmb.pack(side="right", padx=6)
        self.cmb.bind("<<ComboboxSelected>>", lambda e: (self.reshuffle(), self.focus_canvas()))

        # --- нижняя часть: строка состояния и кнопки действий над текущим файлом ---
        self.status = tk.Label(win, text="", bg=BG, fg=MUTED, anchor="w", font=("Arial", 10))
        self.status.pack(fill="x", side="bottom", padx=8, pady=4)
        self.actions = tk.Frame(win, bg=BG)
        self.actions.pack(fill="x", side="bottom", pady=(0, 2))
        self.btn_post = self.make_button(self.actions, _("Открыть пост на сайте (P)"), self.open_post, "#00897b")
        self.btn_post.pack(side="left", padx=6)
        self.btn_file = self.make_button(self.actions, _("Показать файл (O)"), self.open_current, "#37474f")
        self.btn_file.pack(side="left", padx=4)
        self.btn_copy = self.make_button(self.actions, _("Копировать ID (C)"), self.copy_id, "#37474f")
        self.btn_copy.pack(side="left", padx=4)
        self.btn_del = self.make_button(self.actions, _("Удалить… (Del)"), self.action_remove, "#d32f2f")
        self.btn_del.pack(side="right", padx=6)

        self.canvas = tk.Label(win, bg=BG, fg=MUTED, font=("Arial", 14))
        self.canvas.pack(fill="both", expand=True)

        win.bind("<Key>", self.on_key)
        win.bind("<MouseWheel>", lambda e: self.step(-1 if e.delta > 0 else 1))
        self.canvas.bind("<Button-4>", lambda e: self.step(-1))      # колесо в Linux
        self.canvas.bind("<Button-5>", lambda e: self.step(1))
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", lambda e: (self.focus_canvas(), self.step(1)))
        self.canvas.bind("<Enter>", lambda e: self.focus_canvas())   # мышь над картинкой: клавиши идут сюда

        if folder is None:
            try:
                last = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("last_folder")
                folder = Path(last) if last and Path(last).is_dir() else None
            except Exception:
                folder = None
        if folder:
            self.load_folder(Path(folder))
        else:
            self.canvas.config(text=_("Выберите папку кнопкой «Папка…»"))
            self.update_buttons()
        self.win.after(100, self.poll)
        try:
            self.win.lift()
            self.win.focus_force()
        except tk.TclError:
            pass
        self.focus_canvas()

    @staticmethod
    def make_button(parent, text, command, color=None):
        kw = {"bg": color, "fg": "white", "activebackground": color, "activeforeground": "white"} if color else {}
        return tk.Button(parent, text=text, command=command, relief="flat", takefocus=0, **kw)

    def focus_canvas(self):
        try:
            self.canvas.focus_set()
        except tk.TclError:
            pass

    # ---------- клавиши ----------
    def on_key(self, e):
        """Одна точка входа для клавиш: не зависит от раскладки и не мешает вводу в поле интервала."""
        try:
            focus = self.win.focus_get()
        except (KeyError, tk.TclError):
            focus = None
        if focus is not None and focus.winfo_class() in TEXT_WIDGETS:
            if e.keysym in ("Return", "KP_Enter", "Escape"):
                self.focus_canvas()
            return
        if e.state & 0x4:                       # Ctrl+что-то: не трогаем
            return
        action = KEY_ACTIONS.get(e.keysym) or CHAR_ACTIONS.get((e.char or "").lower())
        if not action:
            return
        {
            "next": lambda: self.step(1), "prev": lambda: self.step(-1), "escape": self.exit_fullscreen,
            "remove": self.action_remove, "fullscreen": self.toggle_fullscreen, "reshuffle": self.reshuffle,
            "slideshow": self.toggle_slideshow, "open_file": self.open_current, "toggle_play": self.toggle_play,
            "open_post": self.open_post, "copy_id": self.copy_id,
        }[action]()
        return "break"

    # ---------- папка и порядок ----------
    def choose_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.load_folder(Path(d))
        self.focus_canvas()

    def load_folder(self, path: Path):
        self.root_path = path
        self.lbl_folder.config(text=str(path))
        self.reload()

    def reload(self):
        if self.root_path is None:
            return
        self.all_files = scan_folder(self.root_path, self.var_video.get())
        self.reshuffle()
        self.focus_canvas()

    def reshuffle(self):
        self.stop_slideshow_timer_only()
        if self.root_path is None:
            return
        self.order = apply_filter(self.all_files, self.root_path, self.cmb.get())
        random.shuffle(self.order)
        self.pos = 0
        self.laps = 0
        self.show()
        if self.slideshow_job is not None:
            self.schedule_slideshow()

    # ---------- показ ----------
    def step(self, delta):
        if not self.order:
            return
        self.pos += delta
        if self.pos >= len(self.order):          # круг закончился: перемешиваем заново
            random.shuffle(self.order)
            self.pos = 0
            self.laps += 1
        elif self.pos < 0:
            self.pos = len(self.order) - 1
        self.show()

    def pid_of(self, path: Path):
        """ID поста: из имени файла, иначе из базы программы (если она знает этот файл)."""
        pid = post_id_from_name(path)
        if pid:
            return pid
        if path not in self.pid_cache:
            pid = None
            if self.bridge is not None:
                try:
                    pid = self.bridge.post_id_for(path)
                except Exception as e:
                    log.info("ID для %s определить не удалось: %s", path, e)
                    pid = None
            self.pid_cache[path] = pid
        return self.pid_cache[path]

    def update_buttons(self):
        path = self.current_path()
        has = path is not None
        self.btn_post.config(state="normal" if (has and self.pid_of(path)) else "disabled")
        self.btn_copy.config(state="normal" if has else "disabled")
        self.btn_file.config(state="normal" if has else "disabled")
        can_remove = False
        if has and self.bridge is not None and not self.removing:
            try:
                can_remove = self.bridge.find_root(path) is not None
            except Exception as e:
                log.info("Не удалось определить папку библиотеки для %s: %s", path, e)
                can_remove = False
        self.btn_del.config(state="normal" if can_remove else "disabled")

    def set_status(self, text):
        notice, self.notice = self.notice, ""
        self.status.config(text=(notice + "    " if notice else "") + text)

    def show(self):
        self.stop_player()
        if not self.order:
            self.current_img = None
            self.canvas.config(image="", text=_("В папке нет подходящих файлов") if self.root_path else
                               _("Выберите папку кнопкой «Папка…»"))
            self.set_status("")
            self.update_buttons()
            return
        path = self.order[self.pos]
        try:
            player = make_player(path)
            if player is not None:
                self.start_player(player)
            else:
                self.current_img = load_frame(path)
                self.render()
            w, h = self.current_img.size
            size_kb = path.stat().st_size / 1024
            pid = self.pid_of(path)
            try:
                shown = path.relative_to(self.root_path)
            except ValueError:
                shown = path
            lap = _("  (круг {0})").format(self.laps + 1) if self.laps else ""
            self.set_status(f"{self.pos + 1} / {len(self.order)}{lap}    {shown}    {w}x{h}    "
                            f"{size_kb:.0f} KB" + (f"    ID {pid}" if pid else "") + self.play_info)
        except Exception as e:
            self.stop_player()
            self.current_img = None
            self.canvas.config(image="", text=_("Не удалось открыть:\n{0}\n({1})").format(path.name, e))
            self.set_status(f"{self.pos + 1} / {len(self.order)}    {path}")
        self.update_buttons()

    def display_pil(self, img: Image.Image, resample=Image.BILINEAR):
        """Показывает изображение, вписывая его в окно (увеличение не делается)."""
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        w, h = img.size
        scale = min(cw / w, ch / h, 1.0)
        if scale < 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), resample)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.config(image=self.photo, text="")

    def render(self):
        if self.player is not None and self.last_frame is not None:
            self.display_pil(self.last_frame)
        elif self.current_img is not None:
            self.display_pil(self.current_img, Image.LANCZOS)

    def on_resize(self, event=None):
        if self.resize_job:
            self.win.after_cancel(self.resize_job)
        self.resize_job = self.win.after(120, self.render)

    # ---------- анимации и видео ----------
    def start_player(self, player):
        self.player = player
        self.loops = 0
        self.play_started = time.monotonic()
        self.play_info = player.description
        self.last_frame = player.first
        self.current_img = player.first
        self.display_pil(player.first)
        self.paused = not self.var_play.get()
        self.update_play_button()
        if not self.paused:
            self.player_job = self.win.after(player.delay, self.player_tick)

    def player_tick(self):
        self.player_job = None
        if self.player is None or self.paused:
            return
        t0 = time.monotonic()
        item = self.player.read()
        if item is None:                           # конец: начинаем сначала
            self.loops += 1
            self.player.rewind()
            item = self.player.read()
            if item is None:
                return
        frame, delay = item
        self.last_frame = frame
        self.display_pil(frame)
        wait = max(1, int(delay - (time.monotonic() - t0) * 1000))
        self.player_job = self.win.after(wait, self.player_tick)

    def stop_player(self):
        if self.player_job is not None:
            self.win.after_cancel(self.player_job)
            self.player_job = None
        if self.player is not None:
            self.player.close()
        self.player = None
        self.last_frame = None
        self.play_info = ""
        self.update_play_button()

    def toggle_play(self):
        if self.player is None:
            return
        self.paused = not self.paused
        self.update_play_button()
        if not self.paused and self.player_job is None:
            self.player_job = self.win.after(self.player.delay, self.player_tick)

    def update_play_button(self):
        self.btn_play.config(text=_("Играть (V)") if (self.player is not None and self.paused) else _("Пауза (V)"))

    def close(self):
        self.alive = False
        self.stop_player()
        self.win.destroy()

    # ---------- автопоказ ----------
    def schedule_slideshow(self):
        try:
            sec = max(1, int(self.spin.get()))
        except ValueError:
            sec = 4
        self.slideshow_job = self.win.after(sec * 1000, self.slideshow_tick)

    def slideshow_tick(self):
        playing = self.player is not None and not self.paused
        if playing and self.loops == 0 and time.monotonic() - self.play_started < 120:
            self.slideshow_job = self.win.after(500, self.slideshow_tick)   # ждём конец ролика (не дольше 2 минут)
            return
        self.step(1)
        self.schedule_slideshow()

    def stop_slideshow_timer_only(self):
        if self.slideshow_job is not None:
            self.win.after_cancel(self.slideshow_job)

    def toggle_slideshow(self):
        if self.slideshow_job is None:
            self.btn_slide.config(text=_("Стоп (S)"))
            self.schedule_slideshow()
        else:
            self.stop_slideshow_timer_only()
            self.slideshow_job = None
            self.btn_slide.config(text=_("Автопоказ (S)"))

    # ---------- окно и действия ----------
    def toggle_fullscreen(self):
        self.is_full = not self.is_full
        full = self.is_full
        try:
            self.win.attributes("-fullscreen", full)
        except tk.TclError:
            pass
        if full:
            self.bar.pack_forget()
            self.actions.pack_forget()
        else:
            self.bar.pack(fill="x", side="top", before=self.canvas)
            self.actions.pack(fill="x", side="bottom", pady=(0, 2), before=self.canvas)
        self.focus_canvas()

    def exit_fullscreen(self):
        if self.is_full:
            self.toggle_fullscreen()

    def current_path(self):
        return self.order[self.pos] if self.order else None

    def flash(self, text):
        """Сообщение в строке состояния (до следующего перелистывания)."""
        self.status.config(text=text)

    def open_current(self):
        p = self.current_path()
        if p:
            if self.player is not None and not self.paused:
                self.toggle_play()               # чтобы не играло в двух местах сразу
            open_in_system(p)

    def open_post(self):
        p = self.current_path()
        if not p:
            return
        pid = self.pid_of(p)
        if pid:
            webbrowser.open(f"{BASE_URL}/posts/{pid}")
        else:
            self.flash(_("ID этого файла неизвестен: имя не из цифр и файла нет в базе программы"))

    def copy_id(self):
        p = self.current_path()
        if p:
            pid = self.pid_of(p)
            self.win.clipboard_clear()
            self.win.clipboard_append(str(pid) if pid else p.name)
            self.flash(_("Скопировано: {0}").format(pid if pid else p.name))

    # ---------- удаление ----------
    def action_remove(self):
        """Снять пост с Favorites на сайте (если стоит) и перенести файл в deleted/. Только после подтверждения."""
        path = self.current_path()
        if not path or self.removing:
            return
        if self.bridge is None:
            messagebox.showinfo(_("Недоступно"), _("Удаление работает, когда просмотр запущен из программы "
                                              "Danbooru Library (нужна её база)."), parent=self.win)
            return
        try:
            info = self.bridge.removal_info(path)
        except Exception as e:
            messagebox.showerror(_("Ошибка"), str(e), parent=self.win)
            return
        if info.get("root") is None:
            messagebox.showinfo(_("Папка неизвестна"), _("Эта папка не найдена в базе программы. Откройте её в основной "
                                                   "программе (шаг 1) и выполните шаги 2-3."), parent=self.win)
            return
        if info.get("pid") and info.get("is_fav"):
            text = (_("Пост #{0} будет снят с Favorites на сайте.\nФайл будет перенесён в deleted/ под именем {1}.<расширение>.").format(info['pid'], info['pid']))
        elif info.get("pid"):
            text = (_("Пост #{0} не стоит в ваших Favorites, на сайте ничего не меняется.\nФайл будет перенесён в deleted/.").format(info['pid']))
        else:
            text = _("ID поста неизвестен: Favorites не затрагиваются.\nФайл будет перенесён в deleted/.")
        if info.get("copies", 1) > 1:
            text += _("\nУ файла есть копии ({0}): они тоже будут перенесены.").format(info['copies'] - 1)
        text += (_("\n\nПередумать можно: положите файл обратно в папку, при следующей сверке он будет "
                 "«не в Favorites».\n\nПродолжить?"))
        if not messagebox.askyesno(_("Удалить файл"), text, parent=self.win):
            self.focus_canvas()
            return
        self.removing = True
        self.update_buttons()
        self.flash(_("Убираю…"))

        def work():
            try:
                result = self.bridge.remove(path)
            except Exception as e:
                result = {"ok": False, "message": str(e), "moved": []}
            self.q.put(("removed", path, result))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        """Результаты фоновых действий возвращаются в главный поток через очередь."""
        if not self.alive:
            return
        try:
            while True:
                kind, *args = self.q.get_nowait()
                if kind == "removed":
                    self.finish_remove(*args)
        except queue.Empty:
            pass
        try:
            self.win.after(100, self.poll)
        except tk.TclError:
            pass

    def drop_paths(self, paths):
        gone = set(paths)
        before = sum(1 for p in self.order[:self.pos] if p in gone)
        self.all_files = [p for p in self.all_files if p not in gone]
        self.order = [p for p in self.order if p not in gone]
        self.pos = max(0, self.pos - before)
        if self.pos >= len(self.order):
            self.pos = 0

    def finish_remove(self, path, result):
        self.removing = False
        if result.get("ok"):
            self.drop_paths(result.get("moved") or [path])
            self.notice = result.get("message", _("Убрано"))
            self.show()
        else:
            self.update_buttons()
            messagebox.showerror(_("Не удалось"), result.get("message", _("Ошибка")), parent=self.win)
        self.focus_canvas()


def default_bridge():
    """Для запуска «python random_viewer.py» отдельно: связь с библиотекой, если она установлена рядом."""
    try:
        from .bridges import ViewerBridge
        from .config import get_credentials
        from .net import configure_session
        user, key = get_credentials()
        if user and key:
            configure_session(user, key)
        return ViewerBridge()
    except Exception as e:
        log.info("Просмотр запущен без связи с библиотекой: %s", e)
        return None


def main(argv, bridge=None):
    win = tk.Tk()
    folder = Path(argv[1]) if len(argv) > 1 and Path(argv[1]).is_dir() else None
    Viewer(win, folder, bridge if bridge is not None else default_bridge())
    win.mainloop()


if __name__ == "__main__":
    main(sys.argv)
