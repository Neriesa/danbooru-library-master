# -*- coding: utf-8 -*-

import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .constants import APP_VERSION, BASE_URL, REQUEST_INTERVAL
from .config import CONFIG, log
from .i18n import _


class Cancelled(Exception):
    pass


class ApiError(Exception):
    pass


class PermissionDenied(ApiError):
    """У API-ключа нет нужных прав (повторять запросы бессмысленно)."""


class TagLimitError(ApiError):
    """Слишком много тегов для вашего аккаунта (у бесплатных аккаунтов лимит ниже, чем у Gold)."""


def check_tag_limit(status: int, body: str):
    """Если ответ сайта - отказ из-за числа тегов, бросает TagLimitError с понятным текстом."""
    if status in (400, 422):
        t = (body or "").lower()
        if "taglimit" in t.replace("_", "").replace(" ", "") or ("tags" in t and ("at a time" in t or "more than" in t)):
            raise TagLimitError(_("В запросе слишком много тегов для вашего типа аккаунта. "
                                "У бесплатных аккаунтов лимит ниже, чем у Gold."))


STOP = threading.Event()
_rate_lock = threading.Lock()
_last_request = 0.0
session = requests.Session()


def configure_session(username: str, api_key: str):
    session.auth = (username, api_key)
    session.headers["User-Agent"] = f"DanbooruLibraryMaster/{APP_VERSION} ({username})"


def sleep_or_stop(seconds: float):
    if STOP.wait(seconds):
        raise Cancelled()


def throttle():
    global _last_request
    with _rate_lock:
        wait = REQUEST_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            sleep_or_stop(wait)
        _last_request = time.monotonic()


def api_request(method, url, params=None, data=None, stream=False, timeout=30, max_retries=6):
    """Запрос с повторами при сбоях сети, 429 и 5xx. Не использует окна Tkinter."""
    last_err = None
    for attempt in range(max_retries):
        if STOP.is_set():
            raise Cancelled()
        throttle()
        try:
            r = session.request(method, url, params=params, data=data, stream=stream, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
            log.warning("Сбой сети (%s), попытка %d/%d", e, attempt + 1, max_retries)
            sleep_or_stop(min(60, 2 ** attempt * 2))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"HTTP {r.status_code}"
            try:
                wait = float(r.headers.get("Retry-After", ""))
            except ValueError:
                wait = min(60, 2 ** attempt * 3)
            r.close()
            log.warning("Сервер ответил %s, жду %.0f с", last_err, wait)
            sleep_or_stop(wait)
            continue
        return r
    raise ApiError(_("Не удалось выполнить запрос после {0} попыток: {1}").format(max_retries, last_err))


def api_get(url, params=None, stream=False, timeout=30, max_retries=6):
    return api_request("GET", url, params=params, stream=stream, timeout=timeout, max_retries=max_retries)


def api_json(path: str, params: dict):
    r = api_get(BASE_URL + path, params=params)
    check_tag_limit(r.status_code, r.text)
    if r.status_code in (401, 403):
        raise ApiError(_("Danbooru отклонил логин/API-ключ (HTTP %d). Проверьте config.json.") % r.status_code)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        raise ApiError(_("Danbooru вернул не JSON (возможно, временная ошибка сервера)"))


def lookup_md5(md5: str):
    """Ищет пост по MD5, включая удалённые. Возвращает JSON поста или None."""
    try:
        data = api_json("/posts.json", {"tags": f"md5:{md5} status:any", "limit": 1})
    except (requests.HTTPError, TagLimitError) as e:
        code = e.response.status_code if getattr(e, "response", None) is not None else None
        if not isinstance(e, TagLimitError) and code not in (400, 422):
            raise
        data = api_json("/posts.json", {"tags": f"md5:{md5}", "limit": 1})
    return data[0] if data else None


def add_favorite(post_id: int):
    r = api_request("POST", f"{BASE_URL}/favorites.json", data={"post_id": post_id})
    try:
        if r.status_code in (200, 201):
            return "added"
        if r.status_code in (401, 403):
            raise PermissionDenied(_("Нет прав на добавление в Favorites (HTTP %d). Проверьте права API-ключа.") % r.status_code)
        text = (r.text or "")[:300]
        if r.status_code == 422 and "already" in text.lower():
            return "already"
        raise ApiError(f"HTTP {r.status_code}: {text}")
    finally:
        r.close()


def remove_favorite(post_id: int):
    """Снимает отметку Favorites на сайте. 'removed' - снята, 'already' - её и не было."""
    r = api_request("DELETE", f"{BASE_URL}/favorites/{post_id}.json")
    try:
        if r.status_code in (200, 204):
            return "removed"
        if r.status_code in (401, 403):
            raise PermissionDenied(_("Нет прав на изменение Favorites (HTTP %d). Проверьте права API-ключа.") % r.status_code)
        if r.status_code == 404:
            return "already"
        raise ApiError(f"HTTP {r.status_code}: {(r.text or '')[:300]}")
    finally:
        r.close()


def absolutize(url: str) -> str:
    if url and url.startswith("/"):
        return BASE_URL + url
    return url or ""


def pick_video_variant(post: dict) -> str:
    """
    Ugoira хранится на Danbooru как .zip с кадрами (file_url). Воспроизводимое видео лежит
    в large_file_url / media_asset.variants как .webm или .mp4.
    """
    cands = []
    large = post.get("large_file_url") or ""
    if urlparse(large).path.lower().endswith((".webm", ".mp4")):
        cands.append(large)
    variants = (post.get("media_asset") or {}).get("variants") or []
    variants = sorted(variants, key=lambda v: 0 if v.get("type") == "sample" else 1)
    for v in variants:
        u = v.get("url") or ""
        if urlparse(u).path.lower().endswith((".webm", ".mp4")):
            cands.append(u)
    return absolutize(cands[0]) if cands else ""


def post_to_row(post: dict) -> dict:
    """JSON поста -> строка для таблицы posts."""
    pid = post["id"]
    md5 = (post.get("md5") or "").lower()
    ext = (post.get("file_ext") or (post.get("media_asset") or {}).get("file_ext") or "").lower()
    url = absolutize(post.get("file_url") or "")
    verify, status, note = 1, "pending", None

    if ext == "zip":  # ugoira
        mode = CONFIG.get("ugoira_mode", "webm")  # "webm" | "zip" | "skip"
        if mode == "skip":
            status, note = "skipped", _("ugoira пропущен настройкой ugoira_mode=skip")
        elif mode == "webm":
            url = pick_video_variant(post)
            verify = 0  # webm - пережатое видео, MD5 поста к нему не относится
            if not url:
                status, note = "unavailable", _("для ugoira не найден webm-вариант")

    if status == "pending" and not url:
        status, note = "unavailable", _("нет file_url (пост скрыт или недоступен для вашего аккаунта)")

    final_ext = Path(urlparse(url).path).suffix.lower().lstrip(".") if url else ext
    return {
        "post_id": pid, "md5": md5, "rating": post.get("rating") or "g",
        "file_ext": final_ext or ext or "bin", "url": url, "verify": verify,
        "status": status, "note": note,
        "file_size": post.get("file_size"),
        "width": post.get("image_width"), "height": post.get("image_height"),
        "artist": post.get("tag_string_artist") or "",
        "character": post.get("tag_string_character") or "",
        "copyright": post.get("tag_string_copyright") or "",
        "tags_general": post.get("tag_string_general") or "",
        "deleted": 1 if (post.get("is_deleted") or post.get("is_banned")) else 0,
    }
