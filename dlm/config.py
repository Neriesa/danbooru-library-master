# -*- coding: utf-8 -*-

import json
import logging
import os
from logging.handlers import RotatingFileHandler


from .constants import CONFIG_PATH, LEGACY_CONFIG_PATH, LOG_PATH


log = logging.getLogger("booru")


def setup_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)


def load_config() -> dict:
    """Конфиг лежит в папке данных программы. Конфиг старых версий (рядом со скриптом) переносится один раз."""
    for path in (CONFIG_PATH, LEGACY_CONFIG_PATH):
        if not path.exists():
            continue
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            bad = path.with_name(path.name + ".bad")
            try:
                path.replace(bad)                   # повреждённый конфиг не теряем, но и не мешаем запуску
            except OSError:
                pass
            log.warning("config.json повреждён (%s), сохранён как %s", e, bad.name)
            continue
        if path != CONFIG_PATH:
            try:
                CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
                path.unlink()          # ключ не должен оставаться лежать рядом со скриптом
            except OSError:
                pass
        return cfg
    return {}


def save_config():
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:                                   # другие окна (лента) тоже пишут в этот файл: не затираем их ключи
            merged = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
        except Exception:
            merged = {}
        if "api_key" not in CONFIG:
            merged.pop("api_key", None)        # ключ уехал в системное хранилище
        merged.update(CONFIG)
        CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Не удалось сохранить config.json: %s", e)


CONFIG = load_config()


def developer_mode() -> bool:
    """Служебное (счётчики, HTML-отчёты, папки данных) видно только разработчику. По умолчанию выключено."""
    return bool(CONFIG.get("developer_mode", False))


def set_developer_mode(on: bool):
    CONFIG["developer_mode"] = bool(on)
    save_config()


KEYRING_SERVICE = "DanbooruLibraryMaster"


def _keyring():
    """Системное хранилище паролей (Windows Credential Manager). Если библиотеки нет или оно недоступно - None."""
    if os.environ.get("DLM_NO_KEYRING"):
        return None
    try:
        import keyring
        keyring.get_password(KEYRING_SERVICE, "__probe__")      # проверка, что хранилище реально работает
        return keyring
    except Exception as e:
        log.info("Системное хранилище паролей недоступно (%s): ключ останется в config.json", e)
        return None


def load_api_key(username: str) -> str:
    kr = _keyring()
    if kr and username:
        try:
            value = kr.get_password(KEYRING_SERVICE, username)
            if value:
                return value
        except Exception as e:
            log.warning("Не удалось прочитать ключ из системного хранилища: %s", e)
    return CONFIG.get("api_key", "")


def store_api_key(username: str, key: str) -> bool:
    """Кладёт ключ в системное хранилище. True - ключ в хранилище, а в config.json его нет.
    Если хранилища нет, ключ остаётся в config.json (как раньше)."""
    kr = _keyring()
    if kr and username and key:
        try:
            kr.set_password(KEYRING_SERVICE, username, key)
            CONFIG.pop("api_key", None)
            return True
        except Exception as e:
            log.warning("Не удалось сохранить ключ в системное хранилище: %s", e)
    CONFIG["api_key"] = key
    return False


def migrate_key_to_keyring():
    """Ключ, лежавший в config.json открытым текстом, переносится в системное хранилище (если оно есть)."""
    user, key = CONFIG.get("username", ""), CONFIG.get("api_key", "")
    if user and key and store_api_key(user, key):
        save_config()


def get_credentials():
    user = (os.environ.get("DANBOORU_USER") or CONFIG.get("username", "")).strip()
    key = os.environ.get("DANBOORU_API_KEY") or load_api_key(user)
    return user, key.strip()
