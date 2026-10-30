# -*- coding: utf-8 -*-
"""Английский перевод интерфейса. Ключ - русская строка из кода; {0}, {1}... - подставляемые значения."""

EN = {
    "Аккаунт: не проверен":
        "Account: not checked",
    "Введите логин и API-ключ":
        "Enter your username and API key",
    "Danbooru не принял логин или ключ":
        "Danbooru did not accept the username or key",
    "Неожиданный ответ сайта":
        "Unexpected response from the site",
    "Аккаунт: {0}, уровень не определён: работаю в осторожном режиме":
        "Account: {0}, level unknown: working in cautious mode",
    "Сайт вернул не JSON (возможно, временная ошибка)":
        "The site returned non-JSON data (possibly a temporary error)",
    "Аккаунт: {0} ({1}), запросы до {2} тегов":
        "Account: {0} ({1}), queries up to {2} tags",
    "Аккаунт: {0} ({1}), запросы до {2} тегов: часть режимов ленты работает в упрощённом виде":
        "Account: {0} ({1}), queries up to {2} tags: some Browse modes work in a simplified form",
    "Danbooru временно не отвечает (HTTP {0})":
        "Danbooru is temporarily unavailable (HTTP {0})",
    "Неожиданный ответ сайта: HTTP {0}":
        "Unexpected response from the site: HTTP {0}",
    "Нет связи с Danbooru: {0}":
        "Cannot reach Danbooru: {0}",
    "файл уже был на месте":
        "the file was already in place",
    "MD5 скачанного файла не совпал с MD5 поста":
        "The MD5 of the downloaded file does not match the post's MD5",
    "Добавлено в Favorites: {0}, уже были: {1}, ошибок: {2}":
        "Added to Favorites: {0}, already there: {1}, errors: {2}",
    "Снято с Favorites: {0}, уже не были: {1}, файлов перенесено в {2}/: {3}, ошибок: {4}":
        "Removed from Favorites: {0}, were not there: {1}, files moved to {2}/: {3}, errors: {4}",
    "Читаю теги последних {0} избранных (примерно {1} запросов)…":
        "Reading tags of the last {0} favorites (about {1} requests)…",
    "Теги обновлены по {0} постам":
        "Tags updated from {0} posts",
    "Перенесено из {0}/: {1}, оставлено на месте: {2}":
        "Moved from {0}/: {1}, left in place: {2}",
    "Уже есть в вашей библиотеке (по MD5/ID): {0}":
        "Already in your library (by MD5/ID): {0}",
    "К скачиванию: {0}":
        "To download: {0}",
    "Готово. Скачано: {0}, ошибок: {1}, недоступно: {2}":
        "Done. Downloaded: {0}, errors: {1}, unavailable: {2}",
    "Добавление в Favorites {0}/{1} (пост {2})":
        "Adding to Favorites {0}/{1} (post {2})",
    "Убираю из Favorites {0}/{1} (пост {2})":
        "Removing from Favorites {0}/{1} (post {2})",
    "Теги: обработано постов {0}":
        "Tags: posts processed {0}",
    "Папки {0}/ нет, переносить нечего.":
        "Folder {0}/ does not exist, nothing to move.",
    "Перенос из {0}/: {1}":
        "Moving from {0}/: {1}",
    "неполная загрузка ({0} из {1} байт)":
        "incomplete download ({0} of {1} bytes)",
    "Скачивание {0}/{1} (пост {2})":
        "Downloading {0}/{1} (post {2})",
    "Рейтинг неизвестен, оставлен на месте: {0}":
        "Rating unknown, left in place: {0}",
    "Пост {0}: {1} ({2})":
        "Post {0}: {1} ({2})",
    "Пост {0}: {1}":
        "Post {0}: {1}",
    "Не удалось перенести {0}: {1}":
        "Could not move {0}: {1}",
    "Папка не найдена в базе программы.":
        "The folder was not found in the program's database.",
    "Не заданы логин и API-ключ (шаг 1 основной программы).":
        "Username and API key are not set (step 1 of the main program).",
    "Не удалось":
        "Failed",
    "Пост #{0} снят с Favorites, файл в {1}/":
        "Post #{0} removed from Favorites, the file is in {1}/",
    "Файл перенесён в {0}/ (пост #{1} не был в Favorites)":
        "File moved to {0}/ (post #{1} was not in Favorites)",
    "Файл перенесён в {0}/":
        "File moved to {0}/",
    "Сайт отклонил запрос (HTTP {0}). Проверьте логин и API-ключ.":
        "The site rejected the request (HTTP {0}). Check your username and API key.",
    "автор":
        "artist",
    "персонаж":
        "character",
    "серия":
        "copyright",
    "тег":
        "tag",
    "рейтинг":
        "rating",
    "Популярное":
        "Popular",
    "Лучшее по тегу или автору":
        "Best by tag or artist",
    "Новое по тегу или автору":
        "New by tag or artist",
    "Новое у моих любимых авторов":
        "New from my favorite artists",
    "за день":
        "for a day",
    "за неделю":
        "for a week",
    "за месяц":
        "for a month",
    "прошлый месяц":
        "last month",
    "этот месяц":
        "this month",
    "последние 3 месяца":
        "last 3 months",
    "этот год":
        "this year",
    "прошлый год":
        "last year",
    "всё время":
        "all time",
    "по совпадению с моим вкусом":
        "by match with my taste",
    "по очкам сайта":
        "by site score",
    "по числу избранных":
        "by number of favorites",
    "новые сначала":
        "newest first",
    "случайно":
        "random",
    "сайт принял только упрощённый запрос (ограничение вашего типа аккаунта): список собран без части условий, сортировка по очкам выполняется у вас":
        "the site accepted only a simplified query (a limit of your account type): the list was built without some conditions, and sorting by score is done on your computer",
    "Обзор: лента рекомендаций":
        "Browse: recommendation feed",
    "Загрузить":
        "Load",
    "Обновить с сайта":
        "Refresh from the site",
    "Скрытое…":
        "Hidden…",
    "Открыть на сайте (O)":
        "Open on site (O)",
    "В Favorites (F)":
        "To Favorites (F)",
    "Пропустить (X)":
        "Skip (X)",
    "Скрыть автора (B)":
        "Hide artist (B)",
    "Скрыть тег…":
        "Hide tag…",
    "Крупно (Пробел)":
        "Enlarge (Space)",
    "Выбрать все":
        "Select all",
    "Профиль вкуса":
        "Taste profile",
    "Строю профиль вкуса…":
        "Building the taste profile…",
    "Обновить профиль (≈35 запросов)":
        "Rebuild the profile (≈35 requests)",
    "Загружаю список…":
        "Loading the list…",
    "(автор не указан)":
        "(no artist)",
    "совпадений с вашим профилем нет":
        "no matches with your profile",
    "профиль не построен":
        "profile not built",
    "Скрыть тег":
        "Hide tag",
    "Скрыть выбранные":
        "Hide selected",
    "Скрытое":
        "Hidden",
    "Вернуть выбранные":
        "Restore selected",
    "не удалось прочитать избранное: {0}":
        "could not read favorites: {0}",
    "уже в Favorites":
        "already in Favorites",
    "пропущено вами":
        "skipped by you",
    "мало очков":
        "low score",
    "скрыто вами":
        "hidden by you",
    "знакомый автор":
        "known artist",
    "тег/автор:":
        "tag/artist:",
    "период:":
        "period:",
    "только новые для меня авторы":
        "only artists new to me",
    "показывать пропущенные мной":
        "show posts I skipped",
    "Профиль":
        "Profile",
    "Профиль готов":
        "Profile ready",
    "Ничего не найдено по этим условиям.":
        "Nothing found for these conditions.",
    "Выберите источник и нажмите «Загрузить».":
        "Choose a source and press \"Load\".",
    "\nПопробуйте ослабить фильтры (рейтинг, очки, «только новые авторы»).":
        "\nTry relaxing the filters (rating, score, \"only new artists\").",
    "   Минусы: ":
        "   Cons: ",
    "Загружаю…":
        "Loading…",
    "Фон для сравнения: {0}":
        "Comparison background: {0}",
    "в избранном слишком мало постов для профиля ({0}); нужно хотя бы 60":
        "too few favorites for a profile ({0}); at least 60 are needed",
    "не удалось собрать фон для сравнения ({0} постов)":
        "could not collect the comparison background ({0} posts)",
    "Введите тег или имя автора":
        "Enter a tag or an artist name",
    "лишнее от одного автора":
        "extra from one artist",
    "Сегодня запросов: {0}, трафик: {1:.1f} МБ":
        "Requests today: {0}, traffic: {1:.1f} MB",
    "кандидатов: {0}, показано: {1}":
        "candidates: {0}, shown: {1}",
    "Авторы":
        "Artists",
    "Персонажи":
        "Characters",
    "Серии":
        "Copyrights",
    "Теги":
        "Tags",
    "Рейтинг":
        "Rating",
    "\n\nМинусовые (чего вы избегаете):\n":
        "\n\nNegative (what you avoid):\n",
    "из кэша, без запросов":
        "from cache, no requests",
    "Выберите пост: клик (Ctrl+клик для нескольких) или стрелки.":
        "Select a post: click (Ctrl+click for several) or use the arrow keys.",
    "совпадение с вашим вкусом {0:.0f}%":
        "match with your taste {0:.0f}%",
    "  ({0} выбрано)":
        "  ({0} selected)",
    "Добавить в Favorites":
        "Add to Favorites",
    "Добавляю в Favorites: {0}…":
        "Adding to Favorites: {0}…",
    "Пост #{0}":
        "Post #{0}",
    "Не удалось загрузить картинку":
        "Could not load the image",
    "Избранное: {0}":
        "Favorites: {0}",
    "Источник:":
        "Source:",
    "Сортировка:":
        "Sort:",
    "Рейтинг:":
        "Rating:",
    "очки ≥":
        "score ≥",
    "не больше от автора:":
        "max per artist:",
    "Ctrl+клик: выбрать несколько, пробел: крупно, F: в Favorites, X: пропустить, B: скрыть автора":
        "Ctrl+click: select several, Space: enlarge, F: to Favorites, X: skip, B: hide artist",
    "скрыто ({0})":
        "hidden ({0})",
    "Профиль не построен: {0}":
        "Profile not built: {0}",
    "Не удалось построить профиль:\n{0}":
        "Could not build the profile:\n{0}",
    "Не удалось загрузить: {0}":
        "Could not load: {0}",
    "Не удалось загрузить список.\n{0}":
        "Could not load the list.\n{0}",
    "загружено с сайта":
        "loaded from the site",
    "#{0}  рейтинг {1}  очки {2}  ♥ {3}  {4}x{5}  {6}   {7}{8}\nПочему: {9}.{10}":
        "#{0}  rating {1}  score {2}  ♥ {3}  {4}x{5}  {6}   {7}{8}\nWhy: {9}.{10}",
    "Не удалось добавить:\n":
        "Could not add:\n",
    "Добавлено в Favorites: {0}":
        "Added to Favorites: {0}",
    "Посты с выбранными признаками больше не будут показываться.":
        "Posts with the selected traits will no longer be shown.",
    "Скрытые авторы и теги. Выделите и нажмите «Вернуть».":
        "Hidden artists and tags. Select and press \"Restore selected\".",
    "Сначала постройте профиль вкуса: в нём берутся ваши любимые авторы":
        "First build the taste profile: your favorite artists are taken from it",
    "загружено с сайта; ":
        "loaded from the site; ",
    "▶ видео/анимация":
        "▶ video/animation",
    "Добавить в Favorites постов: {0}?\nЭто изменит ваш аккаунт на Danbooru.":
        "Add posts to Favorites: {0}?\nThis will change your Danbooru account.",
    "Ошибка: {0}":
        "Error: {0}",
    "Скрыто авторов: {0}":
        "Artists hidden: {0}",
    "Построен: {0}\nИзбранных учтено: {1}, фон для сравнения: {2} постов\nПризнаков с весом: {3}\n\n":
        "Built: {0}\nFavorites counted: {1}, comparison background: {2} posts\nTraits with a weight: {3}\n\n",
    "Скрыто признаков: {0}":
        "Traits hidden: {0}",
    "Возвращено: {0}":
        "Restored: {0}",
    "Все":
        "All",
    "В Favorites":
        "In Favorites",
    "Есть на сайте, не в Favorites":
        "On the site, not in Favorites",
    "Пост удалён/забанен на сайте":
        "Post deleted/banned on the site",
    "Не найдено":
        "Not found",
    "Не проверено":
        "Not checked",
    "Художники":
        "Artists",
    "Личный экспериментальный проект, написанный для себя и выложенный как есть: без гарантий и обещаний поддержки. Программа перемещает файлы, поэтому сначала попробуйте её на копии небольшой папки. Danbooru содержит материалы 18+. Проект неофициальный и с Danbooru не связан.":
        "A personal experimental project, written for myself and published as is: no warranties and no promise of support. The program moves files, so try it first on a copy of a small folder. Danbooru contains 18+ material. The project is unofficial and not affiliated with Danbooru.",
    "1. Войдите на Danbooru под своей учётной записью (если её нет, зарегистрируйтесь).\n2. Откройте свой профиль и найдите там раздел «API Keys» (ключи API) в настройках профиля.\n3. Создайте новый ключ и отметьте права. Для просмотра, сверки и докачки достаточно прав на чтение. Для кнопок «в Favorites» и «убрать из Favorites» нужны права на избранное (favorites).\n4. Скопируйте ключ и вставьте его ниже. Ключ равноценен паролю: никому его не показывайте.":
        "1. Sign in to Danbooru with your account (register if you do not have one).\n2. Open your profile and find the \"API Keys\" section in the profile settings.\n3. Create a new key and tick the permissions. Read access is enough for browsing, checking and downloading. The \"to Favorites\" and \"remove from Favorites\" buttons need permissions for favorites.\n4. Copy the key and paste it below. A key is as sensitive as a password: do not show it to anyone.",
    "Проверяю вход…":
        "Checking the sign-in…",
    "О программе":
        "About",
    "Добро пожаловать":
        "Welcome",
    "Логин и API-ключ":
        "Username and API key",
    "Проверить ключ":
        "Check key",
    "Сохранить и продолжить":
        "Save and continue",
    "Введите логин и API-ключ.":
        "Enter your username and API key.",
    "Уровень аккаунта определить не удалось: лента будет работать в осторожном режиме.":
        "The account level could not be determined: the feed will work in cautious mode.",
    "Проверяю…":
        "Checking…",
    "Что будет перенесено":
        "What will be moved",
    "Файл сейчас":
        "File now",
    "Новое имя в other/":
        "New name in other/",
    "Официальная справка Danbooru по API (на английском)":
        "Official Danbooru API help (in English)",
    "Открыть мой профиль на Danbooru":
        "Open my Danbooru profile",
    "У вас Gold или выше: доступны все режимы, запросы до {0} тегов.":
        "You have Gold or higher: all modes are available, queries up to {0} tags.",
    "✓ Вход выполнен: {0} ({1}).\n{2}":
        "✓ Signed in: {0} ({1}).\n{2}",
    "Сохранить без проверки":
        "Save without checking",
    "Справка Danbooru по API":
        "Danbooru API help",
    "Как получить API-ключ":
        "How to get an API key",
    "Логин:":
        "Username:",
    "API-ключ:":
        "API key:",
    "показать":
        "show",
    "У вас бесплатный аккаунт (запросы до {0} тегов). Сверка с сайтом, дубликаты, докачка и просмотр работают полностью. В ленте «Обзор» часть режимов упрощена: сортировка по очкам выполняется на вашем компьютере.":
        "You have a free account (queries up to {0} tags). Checking against the site, duplicates, downloading and the viewer work in full. In Browse some modes are simplified: sorting by score is done on your computer.",
    "{0}\nМожно сохранить данные без проверки и проверить позже.":
        "{0}\nYou can save the details without checking and check later.",
    "Обновить сведения об аккаунте":
        "Refresh account info",
    "Закрыть":
        "Close",
    "К имени добавляется пометка. Если такое имя уже занято, программа подберёт другое. Всё можно вернуть кнопкой «Вернуть из other/» на шаге 4.":
        "A prefix is added to the name. If that name is already taken, the program picks another one. Everything can be undone with the \"Restore from other/\" button in step 4.",
    "Сохранить список в файл":
        "Save the list to a file",
    "Перенести":
        "Move",
    "Не переносить":
        "Do not move",
    "Порядок в вашей коллекции картинок и видео с Danbooru":
        "Order in your collection of Danbooru images and videos",
    "Ключ можно оставить пустым: тогда останется сохранённый.":
        "The key can be left empty: the saved one will be kept.",
    "Выйти":
        "Quit",
    "Отмена":
        "Cancel",
    "{0}. Проверьте логин (без пробелов в начале и конце) и скопируйте ключ целиком.":
        "{0}. Check the username (no spaces at the start or end) and copy the whole key.",
    "Открыть папку данных":
        "Open the data folder",
    "Нечего переносить":
        "Nothing to move",
    "Версия {0}":
        "Version {0}",
    "Папка данных: {0}":
        "Data folder: {0}",
    "Файлов будет перенесено в {0}/: {1}":
        "Files to be moved to {0}/: {1}",
    "  (имя занято)":
        "  (name taken)",
    "Обход папки…":
        "Walking the folder…",
    "Все хэши актуальны":
        "All hashes are up to date",
    "точные копии (MD5)":
        "exact copies (MD5)",
    "похожие (pHash)":
        "similar (pHash)",
    "Файлов в папке: {0}, нужно обработать: {1}":
        "Files in the folder: {0}, to process: {1}",
    "Файлов для сравнения: {0}":
        "Files to compare: {0}",
    "Найдено групп: {0} (точных: {1})":
        "Groups found: {0} (exact: {1})",
    "Отчёт о дубликатах ({0})":
        "Duplicates report ({0})",
    "Групп: {0}":
        "Groups: {0}",
    "Из базы убраны записи о пропавших/перемещённых файлах: {0}":
        "Removed from the database: records of missing or moved files: {0}",
    "=== Группа {0}: {1}, файлов: {2} ===":
        "=== Group {0}: {1}, files: {2} ===",
    "Хэши: {0}":
        "Hashes: {0}",
    "  {0} | {1}x{2} | {3:.1f} KB | расстояние {4}{5}":
        "  {0} | {1}x{2} | {3:.1f} KB | distance {4}{5}",
    "Пропущен {0}: {1}":
        "Skipped {0}: {1}",
    "проверка целостности скопированной базы не пройдена":
        "the integrity check of the copied database failed",
    "База данных перенесена из рабочей папки в {0}":
        "The database was moved from the working folder to {0}",
    "В рабочей папке осталась старая library.db (новая уже есть в {0}); её можно удалить вручную.":
        "An old library.db is left in the working folder (the new one is already in {0}); you can delete it manually.",
    "Перенесено в {0}/ с пометкой в имени: {1}":
        "Moved to {0}/ with a prefix in the name: {1}",
    "Возвращено на прежнее место: {0}, пропущено: {1}":
        "Restored to the original place: {0}, skipped: {1}",
    "Перенос в {0}/: {1}":
        "Moving to {0}/: {1}",
    "Не возвращён (место занято): {0}":
        "Not restored (the place is taken): {0}",
    "Не удалось вернуть {0}: {1}":
        "Could not restore {0}: {1}",
    "нет file_url (пост скрыт или недоступен для вашего аккаунта)":
        "no file_url (the post is hidden or unavailable to your account)",
    "В запросе слишком много тегов для вашего типа аккаунта. У бесплатных аккаунтов лимит ниже, чем у Gold.":
        "The query has too many tags for your account type. Free accounts have a lower limit than Gold.",
    "Не удалось выполнить запрос после {0} попыток: {1}":
        "The request failed after {0} attempts: {1}",
    "Danbooru отклонил логин/API-ключ (HTTP %d). Проверьте config.json.":
        "Danbooru rejected the username/API key (HTTP %d). Check your credentials.",
    "Danbooru вернул не JSON (возможно, временная ошибка сервера)":
        "Danbooru returned non-JSON data (possibly a temporary server error)",
    "ugoira пропущен настройкой ugoira_mode=skip":
        "ugoira skipped by the ugoira_mode=skip setting",
    "Нет прав на добавление в Favorites (HTTP %d). Проверьте права API-ключа.":
        "No permission to add to Favorites (HTTP %d). Check the API key permissions.",
    "Нет прав на изменение Favorites (HTTP %d). Проверьте права API-ключа.":
        "No permission to change Favorites (HTTP %d). Check the API key permissions.",
    "для ugoira не найден webm-вариант":
        "no webm variant found for the ugoira",
    "Только general":
        "General only",
    "Только other":
        "Other only",
    "Без пометок notFound_/siteDeleted_":
        "Without notFound_/siteDeleted_ prefixes",
    "\n\nПередумать можно: положите файл обратно в папку, при следующей сверке он будет «не в Favorites».\n\nПродолжить?":
        "\n\nYou can change your mind: put the file back into the folder, and at the next check it will be \"not in Favorites\".\n\nContinue?",
    "Случайный просмотр":
        "Random viewer",
    "Автопоказ (S)":
        "Slideshow (S)",
    "Пауза (V)":
        "Pause (V)",
    "Открыть пост на сайте (P)":
        "Open post on site (P)",
    "Показать файл (O)":
        "Show file (O)",
    "Копировать ID (C)":
        "Copy ID (C)",
    "Удалить… (Del)":
        "Delete… (Del)",
    "Убираю…":
        "Removing…",
    "встроенный плеер не смог прочитать это видео; нажмите O, чтобы открыть его в системном плеере":
        "the built-in player could not read this video; press O to open it in the system player",
    "    видео {0}без звука (O - в плеере)":
        "    video {0}without sound (O - in the player)",
    "    анимация, {0} кадров":
        "    animation, {0} frames",
    "Папка не выбрана":
        "No folder selected",
    "ID этого файла неизвестен: имя не из цифр и файла нет в базе программы":
        "The ID of this file is unknown: the name is not numeric and the file is not in the program's database",
    "Недоступно":
        "Unavailable",
    "Удаление работает, когда просмотр запущен из программы Danbooru Library (нужна её база).":
        "Deletion works when the viewer is launched from the Danbooru Library program (it needs its database).",
    "Папка неизвестна":
        "Unknown folder",
    "Эта папка не найдена в базе программы. Откройте её в основной программе (шаг 1) и выполните шаги 2-3.":
        "This folder was not found in the program's database. Open it in the main program (step 1) and run steps 2-3.",
    "ID поста неизвестен: Favorites не затрагиваются.\nФайл будет перенесён в deleted/.":
        "The post ID is unknown: Favorites are not touched.\nThe file will be moved to deleted/.",
    "Удалить файл":
        "Delete file",
    "Убрано":
        "Removed",
    "{0:.1f} с, ":
        "{0:.1f} s, ",
    "Папка…":
        "Folder…",
    "Перемешать (R)":
        "Shuffle (R)",
    "Выберите папку кнопкой «Папка…»":
        "Choose a folder with the \"Folder…\" button",
    "Играть (V)":
        "Play (V)",
    "Стоп (S)":
        "Stop (S)",
    "Ошибка":
        "Error",
    "Пост #{0} будет снят с Favorites на сайте.\nФайл будет перенесён в deleted/ под именем {1}.<расширение>.":
        "Post #{0} will be removed from Favorites on the site.\nThe file will be moved to deleted/ as {1}.<extension>.",
    "\nУ файла есть копии ({0}): они тоже будут перенесены.":
        "\nThe file has copies ({0}): they will be moved too.",
    "сек:":
        "sec:",
    "играть анимации":
        "play animations",
    "В папке нет подходящих файлов":
        "There are no suitable files in the folder",
    "  (круг {0})":
        "  (lap {0})",
    "Скопировано: {0}":
        "Copied: {0}",
    "Пост #{0} не стоит в ваших Favorites, на сайте ничего не меняется.\nФайл будет перенесён в deleted/.":
        "Post #{0} is not in your Favorites, so nothing changes on the site.\nThe file will be moved to deleted/.",
    "видео":
        "video",
    "Не удалось открыть:\n{0}\n({1})":
        "Could not open:\n{0}\n({1})",
    "окна создаются":
        "windows can be created",
    "библиотеки":
        "libraries",
    "хэш и база":
        "hash and database",
    "окно":
        "window",
    "папка данных":
        "data folder",
    ", без OpenCV (облегчённая сборка: видео открываются плеером системы)":
        ", without OpenCV (lightweight build: videos open in the system player)",
    "пропущено (нет OpenCV)":
        "skipped (no OpenCV)",
    "чтение и запись видео работают":
        "video reading and writing work",
    "\nИТОГ: есть ошибки":
        "\nSUMMARY: there are errors",
    "\nИТОГ: всё в порядке":
        "\nSUMMARY: all OK",
    "не удалось создать видео (нет кодека mp4v)":
        "could not create a video (no mp4v codec)",
    "видео создано, но не читается":
        "the video was created but cannot be read",
    "<!doctype html><html><head><meta charset='utf-8'><title>Отчёт Danbooru Library Master</title>":
        "<!doctype html><html><head><meta charset='utf-8'><title>Danbooru Library Master report</title>",
    "<p>Поиск по отчёту: <input oninput='f(this.value)' placeholder='автор, персонаж, имя файла…'></p><ul>":
        "<p>Search the report: <input oninput='f(this.value)' placeholder='artist, character, file name…'></p><ul>",
    "Читаю список Избранного (только новые)…":
        "Reading the Favorites list (new items only)…",
    "Читаю весь список Избранного…":
        "Reading the whole Favorites list…",
    "Итог проверки: ":
        "Check result: ",
    "пост удалён или забанен: скачать оригинал может быть нельзя":
        "the post is deleted or banned: the original may not be downloadable",
    "<table><tr><th>Файл</th><th>Пост</th><th>Автор</th><th>Персонажи</th><th>Серия</th><th>Заметка</th></tr>":
        "<table><tr><th>File</th><th>Post</th><th>Artist</th><th>Characters</th><th>Copyright</th><th>Note</th></tr>",
    "ordfav ничего не вернул, пробую fav:…":
        "ordfav returned nothing, trying fav:…",
    "Список Избранного обновлён: просмотрено {0}, новых {1}":
        "Favorites list updated: viewed {0}, new {1}",
    "Уникальных MD5 к проверке: {0}":
        "Unique MD5s to check: {0}",
    "из списка Избранного/кэша":
        "from the Favorites list/cache",
    "не найдено":
        "not found",
    "новых файлов нет":
        "no new files",
    "<h1>Отчёт ({0})</h1>":
        "<h1>Report ({0})</h1>",
    "Список Избранного: страница {0}, постов {1}":
        "Favorites list: page {0}, posts {1}",
    "Пост известен без запросов: {0}":
        "Post known without requests: {0}",
    "Проверка MD5 {0}/{1}":
        "Checking MD5 {0}/{1}",
    "найдено запросом":
        "found by query",
    "Файлов, которые можно перенести в {0}/ с пометкой: {1} (ничего не перенесено)":
        "Files that can be moved to {0}/ with a prefix: {1} (nothing was moved)",
    "Постов, которых больше нет в Избранном: {0}":
        "Posts that are no longer in Favorites: {0}",
    "1. Папка":
        "1. Folder",
    "2. Дубликаты":
        "2. Duplicates",
    "3. Сверка с Danbooru":
        "3. Check against Danbooru",
    "4. Результаты":
        "4. Results",
    "5. Докачка":
        "5. Download",
    "6. Мои теги":
        "6. My tags",
    "Подождите":
        "Please wait",
    "Дождитесь окончания текущей работы и повторите смену языка.":
        "Wait for the current work to finish and change the language again.",
    "Сначала выберите рабочую папку (шаг 1).":
        "First choose a working folder (step 1).",
    "Служебные файлы":
        "Service files",
    "{0}\n\nПодробности записаны в журнал:\n{1}":
        "{0}\n\nDetails are written to the log:\n{1}",
    "Остановлено пользователем.":
        "Stopped by the user.",
    "Не удалось перенести базу в {0}:\n{1}\n\nДанные не потеряны: старая база осталась в рабочей папке.":
        "Could not move the database to {0}:\n{1}\n\nNo data was lost: the old database stayed in the working folder.",
    "ОШИБКА: {0}":
        "ERROR: {0}",
    "Открыть папку служебных файлов":
        "Open the service files folder",
    "Сменить логин / API-ключ":
        "Change username / API key",
    "Обзор рекомендаций":
        "Browse recommendations",
    "Нужен вход":
        "Sign-in required",
    "Для обзора нужны логин и API-ключ: нажмите «Сменить логин / API-ключ».":
        "Browse needs a username and API key: press \"Change username / API key\".",
    "Готово":
        "Done",
    "Логин и ключ сохранены.":
        "Username and key saved.",
    "Сначала выберите рабочую папку.":
        "First choose a working folder.",
    "Мастер библиотеки Danbooru":
        "Danbooru Library Wizard",
    "Выберите папку с вашей коллекцией (подпапки сканируются тоже).\nВаши файлы не перемещаются, пока вы сами не нажмёте соответствующую кнопку.\nВ вашей папке создаются только general/, other/ и deleted/.\nБаза и отчёты хранятся отдельно, чтобы не мозолить глаза.":
        "Choose the folder with your collection (subfolders are scanned too).\nYour files are not moved until you press the corresponding button yourself.\nOnly general/, other/ and deleted/ are created in your folder.\nThe database and reports are stored separately so that they do not clutter your folder.",
    "ВЫБРАТЬ ПАПКУ":
        "CHOOSE FOLDER",
    "Далее ➔":
        "Next ➔",
    "Служебные файлы: {0}":
        "Service files: {0}",
    "Найти дубликаты":
        "Find duplicates",
    "⬅ Назад":
        "⬅ Back",
    "Дальше ➡":
        "Next ➡",
    "Обновить отчёт":
        "Refresh report",
    "К шагу 3 ➔":
        "To step 3 ➔",
    "Отчёт":
        "Report",
    "Нажмите «Найти дубликаты».":
        "Press \"Find duplicates\".",
    "Сравнение файлов…":
        "Comparing files…",
    "Перейти к шагу 3 ➔":
        "Go to step 3 ➔",
    "Дубликатов не найдено (или все обработаны).":
        "No duplicates found (or all handled).",
    "РЕКОМЕНДУЕТСЯ ОСТАВИТЬ":
        "RECOMMENDED TO KEEP",
    "Сохранено:\n{0}":
        "Saved:\n{0}",
    "Дубликаты":
        "Duplicates",
    "Сначала считаются хэши новых файлов (при первом запуске это долго), потом показываются группы. Ничего не удаляется автоматически. Кнопка «В deleted» переносит файл в папку deleted; вернуть можно на шаге 4.":
        "First the hashes of new files are computed (this takes long on the first run), then the groups are shown. Nothing is deleted automatically. The \"To deleted\" button moves a file to the deleted folder; you can restore it in step 4.",
    "Искать и похожие картинки (pHash)":
        "Also look for similar images (pHash)",
    "Порог похожести (0-12):":
        "Similarity threshold (0-12):",
    "Остановлено или ошибка (см. booru_library.log)":
        "Stopped or error (see booru_library.log)",
    "Группа {0} из {1}: {2}, файлов: {3}":
        "Group {0} of {1}: {2}, files: {3}",
    "ТОЧНАЯ КОПИЯ":
        "EXACT COPY",
    "\n✔ есть на Danbooru (ID {0})":
        "\n✔ exists on Danbooru (ID {0})",
    "Открыть":
        "Open",
    "В deleted":
        "To deleted",
    "Не удалось перенести файл:\n{0}":
        "Could not move the file:\n{0}",
    "ПОХОЖЕЕ (расстояние {0})":
        "SIMILAR (distance {0})",
    "Превью недоступно":
        "Preview unavailable",
    "Полностью перечитать список Избранного (медленнее)":
        "Re-read the whole Favorites list (slower)",
    "Перепроверить ранее «не найденные»":
        "Re-check previously \"not found\" files",
    "Сразу переносить «не найденные» и «удалённые на сайте» в other/ с пометкой notFound_ / siteDeleted_ (можно вернуть на шаге 4)":
        "Immediately move \"not found\" and \"deleted on the site\" files to other/ with a notFound_ / siteDeleted_ prefix (can be undone in step 4)",
    "Пробный режим: ничего не переносить, а после сверки показать список и спросить подтверждение":
        "Dry run: move nothing, and after the check show the list and ask for confirmation",
    "Запустить сверку":
        "Start the check",
    "Остановить":
        "Stop",
    "К результатам ➔":
        "To results ➔",
    "Переносить нечего.":
        "Nothing to move.",
    "Перенос отменён: файлы остались на местах.":
        "Move cancelled: the files stayed in place.",
    "Перенос завершён":
        "Move finished",
    "Сверка с Danbooru":
        "Check against Danbooru",
    "Читается список вашего Избранного, затем каждый уникальный MD5 из папки проверяется (сначала по списку, потом запросом к сайту).\nНайденные файлы не трогаются.":
        "The list of your Favorites is read, then every unique MD5 from the folder is checked (first against the list, then by a request to the site).\nFiles that are found are not touched.",
    "HTML-отчёт сохранён: {0}":
        "HTML report saved: {0}",
    "Сверка завершена. Откройте шаг 4.":
        "Check finished. Open step 4.",
    "Остановлено":
        "Stopped",
    "Ошибка (см. журнал)":
        "Error (see the log)",
    "Статус":
        "Status",
    "Файл":
        "File",
    "Пост":
        "Post",
    "Автор":
        "Artist",
    "Персонаж":
        "Character",
    "Заметка":
        "Note",
    "Выбрать все «не в Favorites»":
        "Select all \"not in Favorites\"",
    "Выбрать все «не найдено»":
        "Select all \"not found\"",
    "Выбрать все «удалён на сайте»":
        "Select all \"deleted on the site\"",
    "Открыть пост на сайте":
        "Open post on site",
    "Показать файл":
        "Show file",
    "HTML-отчёт":
        "HTML report",
    "Добавить выбранные в Favorites":
        "Add selected to Favorites",
    "Выбранные «не найдено»/«удалён» → other/":
        "Selected \"not found\"/\"deleted\" → other/",
    "Вернуть из other/ (notFound_, siteDeleted_)":
        "Restore from other/ (notFound_, siteDeleted_)",
    "Вернуть из deleted":
        "Restore from deleted",
    "К докачке ➔":
        "To download ➔",
    "Убрать выбранные из Favorites → deleted":
        "Remove selected from Favorites → deleted",
    "Нет строк":
        "No rows",
    "В текущем списке нет таких файлов. Проверьте фильтр «Показать».":
        "There are no such files in the current list. Check the \"Show\" filter.",
    "Нечего добавлять":
        "Nothing to add",
    "Выделите строки со статусом «Есть на сайте, не в Favorites».":
        "Select rows with the status \"On the site, not in Favorites\".",
    "Добавление в Favorites":
        "Adding to Favorites",
    "Нечего убирать":
        "Nothing to remove",
    "Выделите строки со статусом «В Favorites» или «Пост удалён/забанен на сайте».":
        "Select rows with the status \"In Favorites\" or \"Post deleted/banned on the site\".",
    "Убрать из Favorites":
        "Remove from Favorites",
    "Выделите строки со статусом «Не найдено» или «Пост удалён/забанен на сайте».":
        "Select rows with the status \"Not found\" or \"Post deleted/banned on the site\".",
    "Нечего возвращать":
        "Nothing to restore",
    "В журнале нет перемещений, которые можно отменить.":
        "The log has no moves that can be undone.",
    "Вернуть файлы":
        "Restore files",
    "Данных пока нет: сначала выполните шаг 3 (сверку).":
        "No data yet: run step 3 (the check) first.",
    "Нет поста":
        "No post",
    "Для этого файла пост на Danbooru не найден.":
        "No post was found on Danbooru for this file.",
    "\nЭто изменит ваш аккаунт на Danbooru. Продолжить?":
        "\nThis will change your Danbooru account. Continue?",
    "Добавление завершено":
        "Adding finished",
    "Возвращено: {0}, пропущено: {1}":
        "Restored: {0}, skipped: {1}",
    "Результаты":
        "Results",
    "Показать:":
        "Show:",
    "Поиск (файл, автор, персонаж, серия):":
        "Search (file, artist, character, copyright):",
    "Отметка снимается на сайте, файл уходит в deleted/<id>. Передумали: положите файл обратно в папку.":
        "The mark is removed on the site and the file goes to deleted/<id>. Changed your mind? Put the file back into the folder.",
    "С Favorites на сайте будет снято постов: {0}.\nФайлов будет перенесено в {1}/ (имя <id>.<расширение>): {2}.\n\nПередумать можно так: положите файл обратно в папку, и при следующей сверке он снова станет «не в Favorites» (или кнопка «Вернуть из deleted»).\n\nЭто изменит ваш аккаунт на Danbooru. Продолжить?":
        "Posts to be removed from Favorites on the site: {0}.\nFiles to be moved to {1}/ (name <id>.<extension>): {2}.\n\nYou can change your mind: put the file back into the folder, and at the next check it will be \"not in Favorites\" again (or use the \"Restore from deleted\" button).\n\nThis will change your Danbooru account. Continue?",
    "Перенос в {0}/ ({1} / {2})":
        "Move to {0}/ ({1} / {2})",
    "Вернуть на прежние места файлов: {0}?":
        "Restore files to their previous places: {0}?",
    "Будет добавлено постов в Favorites: {0}.\n":
        "Posts to be added to Favorites: {0}.\n",
    "Пропущено выделенных строк другого статуса: {0}.\n":
        "Selected rows with another status skipped: {0}.\n",
    "Повторить ранее неудавшиеся / недоступные посты":
        "Retry previously failed / unavailable posts",
    "Синхронизировать":
        "Synchronize",
    "Перенести старую папку found/ в general и other":
        "Move the old found/ folder into general and other",
    "Отменить этот перенос":
        "Undo this move",
    "Перенос старой структуры":
        "Moving the old structure",
    "Докачка недостающих файлов из Избранного":
        "Downloading missing files from Favorites",
    "Скачиваются только те посты Избранного, которых нет в вашей папке (сверка по MD5 и ID).\nНовые файлы попадают в general/ (рейтинг general) и other/ (остальные) как <id>.<расширение>. Ваши файлы не затрагиваются.":
        "Only Favorites posts that are not in your folder are downloaded (matched by MD5 and ID).\nNew files go to general/ (rating general) and other/ (the rest) as <id>.<extension>. Your files are not touched.",
    "Папки {0}/ нет.":
        "Folder {0}/ does not exist.",
    "Файлы из {0}/18+ и {1}/Others будут перенесены в {2}/ и {3}/ по рейтингу из базы. Перенос можно отменить. Продолжить?":
        "Files from {0}/18+ and {1}/Others will be moved to {2}/ and {3}/ by the rating from the database. The move can be undone. Continue?",
    "Остановлено или ошибка":
        "Stopped or error",
    "Синхронизация завершена":
        "Synchronization finished",
    "Обновить теги":
        "Update tags",
    "Скрытые теги…":
        "Hidden tags…",
    "Скрытые теги":
        "Hidden tags",
    "Ничего не выбрано":
        "Nothing selected",
    "Выделите теги в списках (можно несколько, с Ctrl).":
        "Select tags in the lists (several with Ctrl).",
    "Тег":
        "Tag",
    "Постов":
        "Posts",
    "Доля":
        "Share",
    "Избранное в базе пусто: выполните сверку (шаг 3) или нажмите «Обновить теги».":
        "The favorites in the database are empty: run the check (step 3) or press \"Update tags\".",
    "Мои теги":
        "My tags",
    "Топ по вашему избранному. Всё лишнее (теги качества, служебные) выделите и нажмите «Скрыть выбранные»: на их место встанут следующие.\nСписок сохраняется и дальше будет основой для подборки новых постов.":
        "The top of your favorites. Select everything unnecessary (quality tags, technical ones) and press \"Hide selected\": the next ones will take their place.\nThe list is saved and will later be the basis for suggesting new posts.",
    "Обновить теги по последним":
        "Update tags for the last",
    "избранных (≈ {0} запросов)":
        "favorites (≈ {0} requests)",
    "Теги обновлены":
        "Tags updated",
    "Эти теги не попадают в топ. Выделите и нажмите «Вернуть».":
        "These tags are excluded from the top. Select and press \"Restore selected\".",
    "В базе избранных постов: {0}. С тегами художников/серий: {1}, с общими тегами: {2}. Чтобы учесть больше, нажмите «Обновить теги».":
        "Favorites posts in the database: {0}. With artist/copyright tags: {1}, with general tags: {2}. Press \"Update tags\" to include more.",
    "Вкл":
        "On",
    "Выкл":
        "Off",
    "Настройки разработчика":
        "Developer settings",
    "Счётчики запросов и трафика, HTML-отчёты, служебные папки и кнопки. Обычному пользователю не нужны.":
        "Request and traffic counters, HTML reports, service folders and buttons. Not needed for normal use.",
    "Для вас":
        "For you",
    "нет миниатюры":
        "no thumbnail",
    "Фильтры…":
        "Filters…",
    "Мой вкус…":
        "My taste…",
    "Сейчас лента общая. Настройте её по вашему избранному: это около минуты, а дальше она учится на каждом вашем решении.":
        "The feed is generic for now. Tune it to your favorites: it takes about a minute, and after that it learns from every decision you make.",
    "Настроить под мой вкус":
        "Tune to my taste",
    "Вернуть (Z)":
        "Undo (Z)",
    "Показать ещё":
        "Show more",
    "Показано: {0}":
        "Showing: {0}",
    "Вкус ещё не настроен: лента учится только на ваших решениях.":
        "Your taste is not set up yet: the feed learns from your decisions only.",
    "Учтено ваших избранных: {0}, обновлено {1}. Лента сразу учитывает и ваши решения в ней.\n\n":
        "Favorites taken into account: {0}, updated {1}. The feed also uses your decisions in it right away.\n\n",
    "Обновить мой вкус":
        "Update my taste",
    "Новых постов больше нет":
        "No more new posts",
    "{0} · новый автор":
        "{0} · new artist",
    "{0}   ★ {1}   ♥ {2}   {3}{4}\nПочему: {5}.{6}":
        "{0}   ★ {1}   ♥ {2}   {3}{4}\nWhy: {5}.{6}",
    "Все посты из этой подборки разобраны. Нажмите «Показать ещё».":
        "All posts in this selection are sorted. Press \"Show more\".",
    "Машина времени":
        "Time machine",
    "годы:":
        "years:",
    "Месяцы: {0}":
        "Months: {0}",
    "В выбранных годах нет прошедших месяцев":
        "The chosen years have no past months",
}
