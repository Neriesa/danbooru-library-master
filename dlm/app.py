# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Danbooru Library Master

Сценарий: у вас есть папка с картинками, и вы не знаете, что из этого есть на Danbooru и что лежит
в ваших Favorites. Программа отвечает на эти вопросы и помогает с решениями.

Папки (создаются внутри выбранной папки):
  general/   - скачанные посты с рейтингом general
  other/     - скачанные посты остальных рейтингов + файлы, не найденные на сайте (в имени пометка
               notFound_) + файлы, чьи посты удалены с сайта (пометка siteDeleted_<id>)
  deleted/   - дубликаты, которые вы убрали кнопкой (не сканируется)
Скачанные файлы называются <id поста>.<расширение>.

Служебные файлы (база, отчёты, конфиг, журнал) в вашей папке НЕ лежат, а хранятся в папке данных
программы (Windows: %LOCALAPPDATA%/DanbooruLibraryMaster). Открыть её можно кнопкой на шаге 1.

Шаги:
  1. Папка        - выбор рабочей папки (подпапки сканируются тоже).
  2. Дубликаты    - считаются MD5 и pHash, затем показываются точные копии и похожие картинки.
                    Ничего не удаляется само.
  3. Сверка       - список Favorites с сайта + проверка каждого уникального MD5 на Danbooru.
                    «Не найденные» и «удалённые на сайте» можно сразу переносить в other/ с пометкой.
  4. Результаты   - таблица и HTML-отчёт, добавление в Favorites, перенос в other/, откат переносов.
  5. Докачка      - скачивает посты из Favorites, которых нет в вашей папке.
  6. Мои теги     - топ художников, персонажей, серий и тегов по вашему избранному; лишнее скрывается вручную.

Убрать пост из Favorites: шаг 4, кнопка «Убрать выбранные из Favorites → deleted». Отметка снимается на сайте,
а файл уходит в deleted/ под именем <id>. Передумали: положите файл обратно в папку, и при следующей сверке он
снова станет «есть на сайте, не в Favorites» (или кнопка «Вернуть из deleted»).

Все переносы пишутся в журнал и отменяются кнопками «Вернуть ...».

Запуск:
  python danbooru_library_master.py            - основная программа
  python danbooru_library_master.py --viewer   - просмотр в случайном порядке (можно добавить путь к папке)
  python danbooru_library_master.py --browse   - обзор: лента новых постов по вашему вкусу
  python danbooru_library_master.py --selftest - проверка окружения без сети (результат в selftest.txt)

Установка зависимостей:  pip install -r requirements.txt
Логин и API-ключ спрашиваются при первом запуске (сменить можно на шаге 1).
Для добавления в Favorites ключу нужны права на запись.
"""

import sys
import tkinter as tk
from pathlib import Path

from . import app_paths

from .config import CONFIG, get_credentials, log, migrate_key_to_keyring, setup_logging
from .net import configure_session
from .db import LibraryDB
from .files import service_dir
from .bridges import BrowseServices, ViewerBridge
from .ui import App, ensure_credentials, report_tk_error
from .selftest import selftest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    setup_logging()
    migrate_key_to_keyring()
    if "--selftest" in argv:
        sys.exit(selftest())
    if "--browse" in argv:                       # лента рекомендаций отдельным ярлыком
        from . import browse
        root = tk.Tk()
        app_paths.set_window_icon(root)
        root.report_callback_exception = report_tk_error
        if not ensure_credentials(root):
            root.destroy()
            return
        configure_session(*get_credentials())
        db, last = None, CONFIG.get("last_folder")
        try:
            if last and (service_dir(Path(last), create=False) / "library.db").exists():
                db = LibraryDB(service_dir(Path(last), create=False) / "library.db")
        except Exception as e:
            log.warning("Не удалось открыть базу последней папки (лента работает без неё): %s", e)
            db = None
        browse.BrowseWindow(root, BrowseServices(db))
        root.mainloop()
        return
    if "--viewer" in argv:                       # тот же .exe открывает просмотр в случайном порядке
        from . import random_viewer
        rest = [a for a in argv if a != "--viewer"]
        user, key = get_credentials()
        if user and key:
            configure_session(user, key)
        random_viewer.main([sys.argv[0]] + rest[:1], ViewerBridge())
        return
    root = tk.Tk()
    app_paths.set_window_icon(root)
    root.report_callback_exception = report_tk_error
    if not ensure_credentials(root):
        root.destroy()
        return
    configure_session(*get_credentials())
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
