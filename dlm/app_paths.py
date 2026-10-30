# -*- coding: utf-8 -*-
"""Общие пути программы: папка данных, конфиг, значок окна. Используется и библиотекой, и просмотрщиком."""

import os
import sys
from pathlib import Path

APP_NAME = "DanbooruLibraryMaster"


def data_base() -> Path:
    """Папка данных программы: конфиг, журнал и служебные файлы библиотек."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / APP_NAME


def config_path() -> Path:
    return data_base() / "config.json"


def resource_path(name: str) -> Path:
    """Файл, лежащий рядом с программой (и внутри собранного .exe тоже)."""
    base = getattr(sys, "_MEIPASS", None)
    return (Path(base) if base else Path(__file__).resolve().parent.parent) / name


def set_window_icon(win) -> None:
    """Значок в заголовке окна (только Windows; если значка нет, ничего не происходит)."""
    if not sys.platform.startswith("win"):
        return
    try:
        icon = resource_path("icon.ico")
        if icon.exists():
            win.iconbitmap(default=str(icon))
    except Exception:
        pass
