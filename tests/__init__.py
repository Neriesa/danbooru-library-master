# -*- coding: utf-8 -*-
"""Окружение тестов: свой поддельный Danbooru, своя папка данных, без системного хранилища ключей.

Запуск:  python -m unittest discover -s tests -t .
Язык интерфейса в тестах задаёт переменная DLM_LANG (ru или en); по умолчанию ru.
GUI-тесты пропускаются, если нет tkinter или дисплея (на Linux: xvfb-run -a python -m unittest ...).
"""

import os
import shutil
import tempfile

from . import mock_danbooru

DATA_DIR = tempfile.mkdtemp(prefix="dlm_test_")
SERVER, URL, STATE = mock_danbooru.start()

os.environ["DLM_BASE_URL"] = URL
os.environ["DLM_NO_KEYRING"] = "1"
os.environ["XDG_DATA_HOME"] = DATA_DIR            # Linux
os.environ["LOCALAPPDATA"] = DATA_DIR             # Windows
os.environ.setdefault("DLM_LANG", "ru")

from dlm import net  # noqa: E402  (после настройки окружения)

net.REQUEST_INTERVAL = 0.0                        # поддельному серверу пауза между запросами не нужна


def tearDownModule():
    shutil.rmtree(DATA_DIR, ignore_errors=True)
