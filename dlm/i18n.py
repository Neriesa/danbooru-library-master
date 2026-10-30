# -*- coding: utf-8 -*-
"""Два языка интерфейса: русский (исходные строки в коде) и английский (словарь в locale_en.py).

Язык выбирается один раз при запуске: переменная DLM_LANG, затем поле "language" в config.json,
затем язык системы (русская Windows -> русский, иначе английский). Смена языка в программе
сохраняет выбор и перезапускает её, поэтому строки можно переводить прямо при импорте.

В коде текст пишется по-русски в обёртке _("..."); для английского ищется перевод по этой строке.
Если перевода нет, показывается русский оригинал (это проверяет tests/test_i18n.py).
"""

import json
import os
import subprocess
import sys

from . import app_paths

LANGS = {"ru": "Русский", "en": "English"}


def _saved_language():
    try:
        cfg = json.loads(app_paths.config_path().read_text(encoding="utf-8"))
        code = str(cfg.get("language", "")).lower()
        return code if code in LANGS else ""
    except Exception:
        return ""


def _system_language():
    try:
        if sys.platform.startswith("win"):
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "ru" if (lang_id & 0x3FF) == 0x19 else "en"
    except Exception:
        pass
    try:
        import locale
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
        return "ru" if str(loc).lower().startswith("ru") else "en"
    except Exception:
        return "en"


def detect_language() -> str:
    env = os.environ.get("DLM_LANG", "").lower()
    if env in LANGS:
        return env
    return _saved_language() or _system_language()


_lang = detect_language()
_catalog = None


def language() -> str:
    return _lang


def _load_catalog():
    global _catalog
    if _catalog is None:
        try:
            from .locale_en import EN
            _catalog = EN
        except Exception:
            _catalog = {}
    return _catalog


def _(text: str) -> str:
    """Перевод строки. Русский - это сам исходный текст."""
    if _lang == "ru":
        return text
    return _load_catalog().get(text, text)


def save_language(code: str):
    """Запоминает выбор языка в config.json (остальные настройки не трогает)."""
    if code not in LANGS:
        return
    path = app_paths.config_path()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        cfg = {}
    cfg["language"] = code
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def restart_program():
    """Запускает программу заново с теми же параметрами; вызывающий после этого закрывает своё окно."""
    if getattr(sys, "frozen", False):
        cmd = [sys.executable] + sys.argv[1:]
    else:
        cmd = [sys.executable] + sys.argv
    subprocess.Popen(cmd, close_fds=True)
