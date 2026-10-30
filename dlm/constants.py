# -*- coding: utf-8 -*-

import os
from pathlib import Path

from . import app_paths
from .i18n import _


APP_VERSION = "1.3.0"
CONFIG_PATH = app_paths.config_path()
LEGACY_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"   # так хранили конфиг старые версии
LOG_PATH = app_paths.data_base() / "booru_library.log"

BASE_URL = os.environ.get("DLM_BASE_URL", "https://danbooru.donmai.us").rstrip("/")   # для тестов можно подставить свой адрес

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}
ARCHIVE_EXT = {".zip"}  # ugoira-архив кадров: сравнивается только по MD5
ALL_EXT = IMAGE_EXT | VIDEO_EXT | ARCHIVE_EXT

GENERAL_DIR = "general"          # скачанные посты с рейтингом general
OTHER_DIR = "other"              # остальные рейтинги + файлы с пометкой notFound_
LEGACY_DIR = "found"             # старая структура found/18+ и found/Others (только чтение и перенос)
TRASH_DIR = "deleted"            # убранные дубликаты (не сканируется)
NOTFOUND_PREFIX = "notFound_"    # пометка в имени файла, не найденного на сайте
SITE_DELETED_PREFIX = "siteDeleted_"  # пометка в имени файла, чей пост удалён с сайта
MARK_BY_CATEGORY = {"not_found": NOTFOUND_PREFIX, "deleted": SITE_DELETED_PREFIX}
MANAGED_DIRS = {GENERAL_DIR, OTHER_DIR, LEGACY_DIR}  # здесь файл <число>.ext = пост с таким ID
SKIP_DIRS = {TRASH_DIR.lower()}


# Чисто служебные теги, которые есть почти у каждого поста и ничего не говорят о вкусе.
# Скрыты по умолчанию, вернуть любой можно в окне «Скрытые теги». Теги качества (highres, absurdres,
# translated и т.п.) на Danbooru относятся к «мета» и в статистику вообще не попадают.
DEFAULT_IGNORED_TAGS = ("solo", "1girl", "1boy", "2girls", "2boys", "3girls", "multiple_girls", "multiple_boys",
                        "looking_at_viewer", "simple_background", "white_background", "grey_background")
TAG_KINDS = (("artist", _("Художники")), ("character", _("Персонажи")), ("copyright", _("Серии")), ("tags_general", _("Теги")))

DEFAULT_PHASH_THRESHOLD = 5
REQUEST_INTERVAL = 0.25
HASH_WORKERS = 4

CATEGORY_ORDER = ["not_fav", "deleted", "not_found", "fav", "unchecked"]
CATEGORY_LABELS = {
    "fav": _("В Favorites"),
    "not_fav": _("Есть на сайте, не в Favorites"),
    "deleted": _("Пост удалён/забанен на сайте"),
    "not_found": _("Не найдено"),
    "unchecked": _("Не проверено"),
}
ALL_LABEL = _("Все")
