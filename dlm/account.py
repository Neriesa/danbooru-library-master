# -*- coding: utf-8 -*-
"""Проверка аккаунта Danbooru: уровень (Free/Gold и выше) и что из этого следует для программы.

Уровень берётся из /profile.json. Лимит тегов в одном запросе у бесплатных аккаунтов ниже, чем у Gold:
основной функционал программы укладывается в 2 тега, а лента «Обзор» при необходимости упрощает запросы.
"""

import time

import requests

from .config import CONFIG, log, save_config
from .constants import APP_VERSION, BASE_URL
from .i18n import _

GOLD_LEVEL = 30
FREE_TAG_LIMIT = 2
GOLD_TAG_LIMIT = 6

LEVEL_BY_NAME = {"restricted": 10, "member": 20, "gold": 30, "platinum": 31, "builder": 32, "contributor": 35,
                 "approver": 37, "moderator": 40, "admin": 50}


class AccountError(Exception):
    """kind: auth - логин/ключ не подошли; network - сайт недоступен; other - всё остальное."""

    def __init__(self, message, kind="other"):
        super().__init__(message)
        self.kind = kind


def parse_account(data: dict, username: str) -> dict:
    """Превращает ответ /profile.json в короткое описание аккаунта."""
    name = str(data.get("level_string") or "").strip()
    level = data.get("level")
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = LEVEL_BY_NAME.get(name.lower())
    explicit = data.get("tag_query_limit")
    if level is None:
        tier, limit = "unknown", FREE_TAG_LIMIT            # уровень неизвестен: считаем осторожно
    elif level >= GOLD_LEVEL:
        tier, limit = "gold", GOLD_TAG_LIMIT
    else:
        tier, limit = "free", FREE_TAG_LIMIT
    if isinstance(explicit, int) and explicit > 0:
        limit = explicit
    return {"username": username, "name": data.get("name") or username, "level": level, "level_string": name or "?",
            "tier": tier, "tag_limit": limit, "checked_at": int(time.time())}


def verify_credentials(username: str, api_key: str, timeout: float = 20) -> dict:
    """Проверяет пару логин / ключ одним лёгким запросом. Ничего не сохраняет."""
    if not username or not api_key:
        raise AccountError(_("Введите логин и API-ключ"), "auth")
    try:
        r = requests.get(BASE_URL + "/profile.json", auth=(username, api_key), timeout=timeout,
                         headers={"User-Agent": f"DanbooruLibraryMaster/{APP_VERSION} ({username})"})
    except (requests.ConnectionError, requests.Timeout) as e:
        raise AccountError(_("Нет связи с Danbooru: {0}").format(e), "network")
    if r.status_code in (401, 403):
        raise AccountError(_("Danbooru не принял логин или ключ"), "auth")
    if r.status_code >= 500 or r.status_code == 429:
        raise AccountError(_("Danbooru временно не отвечает (HTTP {0})").format(r.status_code), "network")
    if r.status_code != 200:
        raise AccountError(_("Неожиданный ответ сайта: HTTP {0}").format(r.status_code), "other")
    try:
        data = r.json()
    except ValueError:
        raise AccountError(_("Сайт вернул не JSON (возможно, временная ошибка)"), "other")
    if not isinstance(data, dict):
        raise AccountError(_("Неожиданный ответ сайта"), "other")
    return parse_account(data, username)


def cached_account(username: str = ""):
    acc = CONFIG.get("account")
    if isinstance(acc, dict) and (not username or str(acc.get("username", "")).lower() == username.lower()):
        return acc
    return None


def store_account(acc: dict):
    CONFIG["account"] = acc
    save_config()


def refresh_account(username: str, api_key: str):
    """Обновляет сведения об аккаунте при запуске. Без сети возвращает последние известные (или None)."""
    try:
        acc = verify_credentials(username, api_key)
    except AccountError as e:
        log.warning("Проверка аккаунта не удалась (%s): %s", e.kind, e)
        return cached_account(username)
    store_account(acc)
    return acc


def current_tag_limit() -> int:
    acc = cached_account()
    return int(acc["tag_limit"]) if acc else FREE_TAG_LIMIT


def describe(acc) -> str:
    """Одна строка для окна."""
    if not acc:
        return _("Аккаунт: не проверен")
    if acc.get("tier") == "gold":
        return _("Аккаунт: {0} ({1}), запросы до {2} тегов").format(acc.get('name'), acc.get('level_string'), acc.get('tag_limit'))
    if acc.get("tier") == "free":
        return (_("Аккаунт: {0} ({1}), запросы до {2} тегов: часть режимов ленты работает в упрощённом виде").format(acc.get('name'), acc.get('level_string'), acc.get('tag_limit')))
    return _("Аккаунт: {0}, уровень не определён: работаю в осторожном режиме").format(acc.get('name'))

