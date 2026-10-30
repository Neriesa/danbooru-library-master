# Changelog / История изменений

Формат: [Keep a Changelog](https://keepachangelog.com/). Версии: `MAJOR.MINOR.PATCH`.

## [1.3.0] - 2026-10-30

### Добавлено / Added
- **Настройки разработчика:** переключатель в окне «О программе», по умолчанию выключен. Счётчики запросов и трафика, HTML-отчёт и отчёт о дубликатах, служебные папки, кнопка «Обновить с сайта» и подробная статистика теперь видны только при включённом режиме. Отчёты без него не создаются. / Developer settings switch in "About", off by default: counters, HTML and duplicate reports, service folders and "Refresh from site" appear only when it is on, and reports are not written without it.
- **Лента: источник «Для вас»** (по умолчанию) ищет посты по вашим персонажам, сериям, тегам и авторам, а не только пересортировывает популярное. Загружается сама при открытии. / Browse: a default "For you" source finds posts from your taste and loads on open.
- **Лента учится на решениях:** «в Favorites» и «Пропустить» сразу меняют сортировку, профиль перестраивать не нужно. Кнопка «Вернуть (Z)» отменяет пропуск. / Browse learns from Favorite and Skip immediately; Undo (Z) reverts a skip.
- **Лента: «Машина времени».** Выбираете годы, каждая загрузка берёт 4 случайных месяца, разнесённых по этому промежутку: лучшее за месяц и находки по вашему вкусу. Посещённые месяцы не повторяются, пока промежуток не исчерпан. / Browse: "Time machine" draws 4 random months spread across chosen years, with each month's best plus taste matches, without repeating months until the span is used up.
- «Показать ещё», подпись причины и пометка «новый автор» на карточке. / "Show more", a reason and a "new artist" mark on cards.

### Изменено / Changed
- Сортировка: длина списка тегов больше не даёт преимущества, учитываются очки сайта, разнообразие авторов/персонажей/серий и то, что уже показывали. Процент совпадения теперь сравнивается с вашими избранными (нужно обновить профиль). / Ranking no longer rewards long tag lists and adds quality, diversity and freshness; the match percentage now compares against your favorites (update the profile to get it).
- Фильтры свёрнуты, предложение построить профиль стало полосой над лентой вместо окна. / Filters are collapsed; the profile prompt is a banner, not a dialog.

### Исправлено / Fixed
- «Популярное» запрашивало только страницу по умолчанию вместо 100 постов. / Popular fetched only the default page instead of 100 posts.
- Сортировка «случайно» всегда давала один и тот же порядок. / "Random" sort always gave the same order.
- Кэш крупных картинок не работал между запусками. / The large image cache did not survive restarts.
- Посты без миниатюры показывались пустыми карточками. / Posts without a thumbnail appeared as blank cards.

## [1.2.0] - 2026-10-20

### Добавлено / Added
- **Два языка интерфейса, русский и английский.** Выбор при первом запуске (по языку системы) и в окне «О программе»; смена перезапускает программу. / Russian and English UI; chosen from the system language, switchable in "About".
- **Окно первого запуска:** пошаговая инструкция, ссылка на справку Danbooru по API, кнопка «Проверить ключ». / First-run window with API key instructions, a link to Danbooru's API help and a "Check key" button.
- **Проверка типа аккаунта (Free / Gold и выше).** Основной функционал работает у всех; лента «Обзор» у бесплатных аккаунтов автоматически упрощает запросы и сообщает об этом. / Account tier check; Browse falls back to simpler queries on free accounts.
- **Пробный режим перемещений:** список «что будет перенесено» с подтверждением и сохранением в файл (шаг 3 и шаг 4). / Dry-run preview before moving files.
- **Окно «О программе»** с дисклеймером, сведениями об аккаунте и папкой данных. / About window.
- **API-ключ хранится в системном хранилище** (Windows Credential Manager) через `keyring`; без него остаётся в `config.json`. / API key stored in the system keyring when available.
- Выбор рейтингов в ленте запоминается (по умолчанию показываются все). / Browse remembers the rating filter.
- Автотесты (`tests/`), поддельный Danbooru для проверок без сети, GitHub Actions. / Automated tests, a mock Danbooru server, CI.

### Изменено / Changed
- Код разбит на модули пакета `dlm/` (сеть, база, файлы, хэши, дубликаты, перемещения, диалоги, по файлу на шаг окна). Запуск прежний: `python danbooru_library_master.py`. / The code was split into the `dlm/` package.
- Ошибки, которые раньше молча проглатывались, теперь попадают в журнал; повреждённый `config.json` сохраняется как `config.json.bad`, а не теряется. / Previously silent errors are now logged.
- Для проверки прав ключа вместо поиска слова в тексте ошибки используется отдельный тип ошибки. / Permission errors use a dedicated exception type.
- Ярлыки получают названия на языке системы. / Shortcut names follow the system language.

## [1.1] - 2026-10

- Лента рекомендаций «Обзор», случайный просмотр с видео и анимацией, «Мои теги», сборка `.exe` с ярлыками. / Browse feed, random viewer, My tags, `.exe` build.
