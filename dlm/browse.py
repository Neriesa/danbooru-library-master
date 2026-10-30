# -*- coding: utf-8 -*-
"""
Обзор: лента новых и популярных постов Danbooru, отсортированная по вашему вкусу.

Что делает:
  * строит профиль вкуса по вашему избранному (веса тегов: автор, персонаж, серия, общие теги, рейтинг);
  * «Для вас» сам ищет кандидатов по вашим персонажам, сериям, тегам и авторам и добавляет популярное; остальные
    источники: популярное, лучшее по тегу или автору за период, новое, новое у любимых авторов;
  * «Машина времени» берёт случайные месяцы из выбранных лет: лучшее за месяц и находки по вашему вкусу;
  * убирает то, что уже в Favorites, пропущено или скрыто, и сортирует: вкус, качество, разнообразие, свежесть показа;
  * показывает сетку миниатюр: открыть на сайте, добавить в Favorites, пропустить, скрыть автора или тег.
Сеть: запросы лёгкие (параметр only), результаты кэшируются, оригиналы не скачиваются.
Решения (добавил, пропустил, скрыл) запоминаются, в ленте повторно не появляются и сразу учитываются в сортировке.

Клавиши (работают и в русской раскладке): стрелки - выбор, Пробел - крупно, F (А) - в Favorites,
X (Ч) - пропустить, Z (Я) - вернуть пропущенное, O (Щ) или Enter - открыть на сайте, B (И) - скрыть автора, Ctrl+A - выбрать все, Esc - закрыть.
"""

import bisect
import json
import math
import queue
import random
import sqlite3
import threading
import time
import webbrowser
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

import requests
from PIL import Image, ImageTk

from . import app_paths
from .config import developer_mode, log
from .net import PermissionDenied, TagLimitError
from .i18n import _

FIELDS_LIGHT = "id,rating,score,fav_count,tag_string_artist,tag_string_character,tag_string_copyright,tag_string_general"
FIELDS_BROWSE = FIELDS_LIGHT + ",preview_file_url,file_ext,image_width,image_height,created_at"

MIN_EVIDENCE, WEIGHT_CAP, Z_MIN = 3, 3.0, 2.0
MULT = {"a": 2.0, "c": 1.5, "s": 1.0, "t": 0.7, "r": 1.0}      # «автор и персонаж важнее» (лучший вариант проверки)
KIND_NAMES = {"a": _("автор"), "c": _("персонаж"), "s": _("серия"), "t": _("тег"), "r": _("рейтинг")}
CACHE_HOURS = 6
THUMB, CARD_W, CARD_H = 180, 196, 264
THUMB_CACHE_MB = 300

QUALITY_WEIGHT = 0.15            # сколько в сортировке значат очки сайта рядом со вкусом
SHOWN_PENALTY, SHOWN_DAYS, SHOWN_TOP = 0.6, 30, 40      # уже показанное опускается, чтобы лента не повторялась
DIVERSITY_STEP, DIVERSITY_HEAD = 0.4, 120
REPEAT_COST = {"a": 1.0, "c": 0.6, "s": 0.3, "d": 0.2}  # насколько утомляет повтор автора, персонажа, серии, месяца
LEARN_POS, LEARN_NEG, LEARN_CAP = 0.3, 0.1, 1.5         # «в Favorites» учит сильнее, чем «пропустить»
SEED_MIX = (("c", 4), ("s", 2), ("t", 3), ("a", 3))     # сколько запросов «Для вас» на каждый вид признака
FOR_YOU_DAYS, FOR_YOU_PER_SEED, POPULAR_PER_PAGE = 180, 30, 100
TIME_MONTHS, TIME_PER_MONTH, TIME_PER_SEED, TIME_SEEDS = 4, 40, 20, 2     # за один заход: месяцы и запросы на каждый
FIRST_YEAR = 2005                # год запуска Danbooru

POPULAR_PATH = "/explore/posts/popular.json"
SOURCES = [_("Для вас"), _("Машина времени"), _("Популярное"), _("Лучшее по тегу или автору"), _("Новое по тегу или автору"),
           _("Новое у моих любимых авторов")]
SRC_FOR_YOU, SRC_TIME, SRC_POPULAR, SRC_BEST, SRC_NEW, SRC_ARTISTS = SOURCES
POP_SCALES = {_("за день"): "day", _("за неделю"): "week", _("за месяц"): "month"}
PERIODS = [_("прошлый месяц"), _("этот месяц"), _("последние 3 месяца"), _("этот год"), _("прошлый год"), _("всё время")]
SORTS = [_("по совпадению с моим вкусом"), _("по очкам сайта"), _("по числу избранных"), _("новые сначала"), _("случайно")]
RATING_ORDER = "gsqe"
RATING_NAMES = {"g": "general", "s": "sensitive", "q": "questionable", "e": "explicit"}


def load_saved_ratings() -> set:
    """Какие рейтинги показывать в ленте. По умолчанию все; выбор хранится в config.json (ключ browse_ratings)."""
    path = app_paths.config_path()
    if not path.exists():
        return set(RATING_ORDER)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        value = str(cfg.get("browse_ratings", RATING_ORDER))
        chosen = {c for c in value if c in RATING_ORDER}
        return chosen or set(RATING_ORDER)
    except Exception as e:
        log.warning("Не удалось прочитать выбор рейтингов: %s", e)
        return set(RATING_ORDER)


def save_ratings(chosen: set):
    path = app_paths.config_path()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        cfg["browse_ratings"] = "".join(c for c in RATING_ORDER if c in chosen)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Не удалось сохранить выбор рейтингов: %s", e)

BG, BG2, FG, MUTED = "#1a1a1a", "#2d2d2d", "#ffffff", "#b0bec5"
GREEN, RED, TEAL, GREY, ORANGE = "#4caf50", "#d32f2f", "#00897b", "#37474f", "#ef6c00"

KEY_ACTIONS = {"Right": "next", "Down": "next", "Left": "prev", "Up": "prev", "space": "preview",
               "Return": "open_site", "Escape": "escape"}
CHAR_ACTIONS = {}
for _action, _chars in {"favorite": "f\u0430", "skip": "x\u0447", "undo": "z\u044f", "open_site": "o\u0449",
                        "block_author": "b\u0438"}.items():
    for _ch in _chars:
        CHAR_ACTIONS[_ch] = _action
TEXT_WIDGETS = {"Spinbox", "TSpinbox", "Entry", "TEntry", "TCombobox", "Text"}


# ============================ модель вкуса ============================

def slim(p: dict) -> dict:
    return {"id": p.get("id"), "rating": p.get("rating") or "", "score": p.get("score") or 0,
            "fav_count": p.get("fav_count") or 0,
            "a": p.get("tag_string_artist") or "", "c": p.get("tag_string_character") or "",
            "s": p.get("tag_string_copyright") or "", "t": p.get("tag_string_general") or "",
            "preview": p.get("preview_file_url") or "", "ext": p.get("file_ext") or "",
            "w": p.get("image_width") or 0, "h": p.get("image_height") or 0,
            "created": (p.get("created_at") or "")[:10]}


def tokens(p: dict, ignored) -> set:
    out = {"r:" + p["rating"]} if p.get("rating") else set()
    for kind in "acst":
        for tag in (p.get(kind) or "").split():
            if tag not in ignored:
                out.add(f"{kind}:{tag}")
    return out


def train(fav_tokens, bg_tokens):
    """Вес признака = log(как часто он у вас / как часто в обычных постах), только если отличие статистически заметно."""
    n_fav, n_bg = Counter(), Counter()
    for t in fav_tokens:
        n_fav.update(t)
    for t in bg_tokens:
        n_bg.update(t)
    nf, nb = len(fav_tokens), len(bg_tokens)
    weights = {}
    for tok in set(n_fav) | set(n_bg):
        a, b = n_fav[tok], n_bg[tok]
        if a + b < MIN_EVIDENCE:
            continue
        pooled = (a + b) / (nf + nb)
        se = math.sqrt(max(pooled * (1 - pooled), 1e-9) * (1 / nf + 1 / nb))
        z = (a / nf - b / nb) / se
        if abs(z) < Z_MIN:
            continue
        raw = max(-WEIGHT_CAP, min(WEIGHT_CAP, math.log(((a + 1) / (nf + 2)) / ((b + 2) / (nb + 4)))))
        weights[tok] = raw * (1 - Z_MIN / abs(z))
    return weights, n_fav


def score_tokens(toks, weights) -> float:
    return sum(weights.get(t, 0.0) * MULT[t[0]] for t in toks)


def taste_score(toks, weights) -> float:
    """Оценка для сортировки: корень из числа признаков убирает преимущество постов, где просто больше тегов."""
    vals = [weights[t] * MULT[t[0]] for t in toks if t in weights]
    return sum(vals) / math.sqrt(len(vals)) if vals else 0.0


def learned_weights(weights, signals) -> dict:
    """Веса профиля плюс решения в ленте: signals = {признак: (добавлено, пропущено)}."""
    out = dict(weights)
    for tok, (pos, neg) in signals.items():
        delta = max(-LEARN_CAP, min(LEARN_CAP, LEARN_POS * pos - LEARN_NEG * neg))
        if delta:
            out[tok] = out.get(tok, 0.0) + delta
    return out


def diversify(pool):
    """Жадный порядок: каждый повтор автора, персонажа или серии отодвигает пост, лента не состоит из одного и того же."""
    rest, tail, out, seen = pool[:DIVERSITY_HEAD], pool[DIVERSITY_HEAD:], [], Counter()

    def facets(item):
        found = [t for t in item["toks"] if t[0] in REPEAT_COST]
        return found + ["d:" + item["created"][:7]] if item.get("created") else found

    def value(item):
        return item["rank"] - DIVERSITY_STEP * sum(seen[t] * REPEAT_COST[t[0]] for t in facets(item))

    while rest:
        best = rest.pop(max(range(len(rest)), key=lambda i: value(rest[i])))
        seen.update(facets(best))
        out.append(best)
    return out + tail


def explain(toks, weights, k=4):
    """Что сильнее всего подняло и опустило оценку: [(признак, вклад), ...]."""
    contrib = sorted(((weights.get(t, 0.0) * MULT[t[0]], t) for t in toks if weights.get(t, 0.0)), reverse=True)
    pos = [(t, c) for c, t in contrib if c > 0][:k]
    neg = [(t, c) for c, t in contrib[::-1] if c < 0][:2]
    return pos, neg


def describe(token: str) -> str:
    return f"{KIND_NAMES[token[0]]} {token[2:]}"


def match_percent(score: float, bg_scores) -> float:
    """Выше какой доли образцов стоит пост. Образцы - ваши избранные (50 = как обычный ваш избранный пост)."""
    if not bg_scores:
        return 0.0
    return 100.0 * bisect.bisect_left(bg_scores, score) / len(bg_scores)


# ============================ хранилище ============================

class Store:
    """Небольшая база обзора: профиль, решения, скрытое, кэш запросов, счётчик трафика."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        with self.lock:
            c = self.conn
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS seen (post_id INTEGER PRIMARY KEY, state TEXT NOT NULL, ts REAL)")
            c.execute("CREATE TABLE IF NOT EXISTS block (token TEXT PRIMARY KEY, ts REAL)")
            c.execute("CREATE TABLE IF NOT EXISTS qcache (key TEXT PRIMARY KEY, ts REAL, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS signal (token TEXT PRIMARY KEY, pos INTEGER NOT NULL DEFAULT 0, "
                      "neg INTEGER NOT NULL DEFAULT 0)")
            c.execute("CREATE TABLE IF NOT EXISTS shown (post_id INTEGER PRIMARY KEY, n INTEGER NOT NULL, ts REAL)")
            c.commit()

    def get_meta(self, key, default=None):
        with self.lock:
            r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def set_meta(self, key, value):
        with self.lock:
            self.conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                              (key, value))
            self.conn.commit()

    # профиль
    def load_profile(self):
        raw = self.get_meta("profile")
        return json.loads(raw) if raw else None

    def save_profile(self, profile: dict):
        self.set_meta("profile", json.dumps(profile, ensure_ascii=False))

    # решения
    def mark_seen(self, ids, state):
        with self.lock:
            self.conn.executemany("INSERT INTO seen (post_id, state, ts) VALUES (?, ?, ?) "
                                  "ON CONFLICT(post_id) DO UPDATE SET state=excluded.state, ts=excluded.ts",
                                  [(i, state, time.time()) for i in ids])
            self.conn.commit()

    def seen_map(self) -> dict:
        with self.lock:
            return dict(self.conn.execute("SELECT post_id, state FROM seen").fetchall())

    def unmark_seen(self, ids):
        with self.lock:
            self.conn.executemany("DELETE FROM seen WHERE post_id=?", [(i,) for i in ids])
            self.conn.commit()

    # чему лента научилась на решениях
    def signal_add(self, toks, pos=0, neg=0):
        with self.lock:
            self.conn.executemany("INSERT INTO signal (token, pos, neg) VALUES (?, ?, ?) "
                                  "ON CONFLICT(token) DO UPDATE SET pos=pos+excluded.pos, neg=neg+excluded.neg",
                                  [(t, pos, neg) for t in toks])
            self.conn.commit()

    def signals(self) -> dict:
        with self.lock:
            return {r[0]: (r[1], r[2]) for r in self.conn.execute("SELECT token, pos, neg FROM signal")}

    # что уже показывали
    def mark_shown(self, ids):
        with self.lock:
            self.conn.executemany("INSERT INTO shown (post_id, n, ts) VALUES (?, 1, ?) "
                                  "ON CONFLICT(post_id) DO UPDATE SET n=n+1, ts=excluded.ts",
                                  [(i, time.time()) for i in ids])
            self.conn.commit()

    def shown_map(self) -> dict:
        since = time.time() - SHOWN_DAYS * 86400
        with self.lock:
            return dict(self.conn.execute("SELECT post_id, n FROM shown WHERE ts>=?", (since,)).fetchall())

    # скрытое: токены вида a:имя, c:имя, s:имя, t:тег
    def block_add(self, toks):
        with self.lock:
            self.conn.executemany("INSERT OR REPLACE INTO block (token, ts) VALUES (?, ?)", [(t, time.time()) for t in toks])
            self.conn.commit()

    def block_remove(self, toks):
        with self.lock:
            self.conn.executemany("DELETE FROM block WHERE token=?", [(t,) for t in toks])
            self.conn.commit()

    def blocked(self) -> set:
        with self.lock:
            return {r[0] for r in self.conn.execute("SELECT token FROM block")}

    # кэш запросов
    def qcache_get(self, key, max_hours):
        with self.lock:
            r = self.conn.execute("SELECT ts, data FROM qcache WHERE key=?", (key,)).fetchone()
        if r and time.time() - r[0] < max_hours * 3600:
            return json.loads(r[1])
        return None

    def qcache_set(self, key, data):
        with self.lock:
            self.conn.execute("INSERT INTO qcache (key, ts, data) VALUES (?, ?, ?) "
                              "ON CONFLICT(key) DO UPDATE SET ts=excluded.ts, data=excluded.data",
                              (key, time.time(), json.dumps(data, ensure_ascii=False)))
            self.conn.commit()

    # трафик за сегодня
    def add_traffic(self, requests_n, nbytes):
        key = "net:" + date.today().isoformat()
        with self.lock:
            cur = json.loads(self.get_meta(key, '{"req": 0, "bytes": 0}'))
            cur["req"] += requests_n
            cur["bytes"] += nbytes
            self.set_meta(key, json.dumps(cur))

    def traffic_today(self):
        cur = json.loads(self.get_meta("net:" + date.today().isoformat(), '{"req": 0, "bytes": 0}'))
        return cur["req"], cur["bytes"]

    def close(self):
        with self.lock:
            self.conn.close()


# ============================ получение данных ============================

def api(services, store, path, params):
    data, nbytes = services.api_json(path, params)
    store.add_traffic(1, nbytes)
    return data


def get_posts(services, store, path, params, pages=1, per_page=100, first_page=1):
    """Список постов с постраничным чтением. Если сайт не принимает only, повторяет без него."""
    use_only, out = True, []
    for page in range(first_page, first_page + pages):
        q = dict(params)
        q.update(limit=per_page, page=page)
        if use_only:
            q["only"] = FIELDS_BROWSE
        try:
            data = api(services, store, path, q)
        except TagLimitError:
            raise
        except Exception:
            if not use_only:
                raise
            use_only = False
            q.pop("only", None)
            data = api(services, store, path, q)
        out += data
        if len(data) < per_page:
            break
    return out


def get_posts_fallback(services, store, variants, state, pages=1, per_page=100, first_page=1):
    """Запрос с запасными вариантами: от полного к простому. Сайт отказал из-за числа тегов - берём следующий.
    state["level"] запоминает, какой вариант сработал, чтобы остальные запросы сразу шли с ним."""
    last = None
    for i in range(state.get("level", 0), len(variants)):
        try:
            posts = get_posts(services, store, "/posts.json", {"tags": variants[i]}, pages=pages, per_page=per_page,
                              first_page=first_page)
            if i > state.get("level", 0):
                state["level"] = i
            if i > 0:
                state["simplified"] = True
            return posts
        except TagLimitError as e:
            last = e
    raise last


def fetch_favorites_light(services, store, max_fav, progress):
    last = None
    for tags, use_only in ((f"ordfav:{services.username}", True), (f"ordfav:{services.username}", False),
                           (f"fav:{services.username}", True), (f"fav:{services.username}", False)):
        params = {"tags": tags, "limit": 100, "page": 1}
        if use_only:
            params["only"] = FIELDS_LIGHT
        try:
            data = api(services, store, "/posts.json", params)
        except Exception as e:
            last = e
            continue
        if not data:
            continue
        posts, page = [slim(p) for p in data], 1
        while len(data) >= 100 and len(posts) < max_fav:
            page += 1
            data = api(services, store, "/posts.json", {**params, "page": page})
            if not data:
                break
            posts += [slim(p) for p in data]
            progress(_("Избранное: {0}").format(len(posts)))
        return posts[:max_fav]
    raise RuntimeError(_("не удалось прочитать избранное: {0}").format(last))


def fetch_background(services, store, fav_ids, n, progress):
    """Обычные посты того же времени, что и ваши избранные (срезы id:<N, быстрые для сайта)."""
    rng = random.Random(7)
    ids = list(fav_ids)
    seen, posts, tries, failures, use_only = set(), [], 0, 0, True
    while len(posts) < n and tries < (n // 50) * 3 + 3:
        tries += 1
        params = {"tags": f"id:<{rng.choice(ids) + rng.randint(1, 5000)}", "limit": 50}
        if use_only:
            params["only"] = FIELDS_LIGHT
        try:
            data = api(services, store, "/posts.json", params)
        except Exception:
            if use_only:
                use_only = False
                continue
            failures += 1
            if failures >= 3:
                if len(posts) >= 150:
                    break
                raise
            continue
        for p in data:
            if p.get("id") not in seen:
                seen.add(p["id"])
                posts.append(slim(p))
        progress(_("Фон для сравнения: {0}").format(len(posts)))
    return posts[:n]


def build_profile(services, store, progress, max_fav=1500, bg_n=1000):
    """Профиль вкуса: веса признаков + распределение оценок обычных постов (для «совпадения, %»)."""
    ignored = set(services.ignored_tags())
    favs = fetch_favorites_light(services, store, max_fav, progress)
    if len(favs) < 60:
        raise RuntimeError(_("в избранном слишком мало постов для профиля ({0}); нужно хотя бы 60").format(len(favs)))
    bg = fetch_background(services, store, [p["id"] for p in favs if p.get("id")], bg_n, progress)
    if len(bg) < 150:
        raise RuntimeError(_("не удалось собрать фон для сравнения ({0} постов)").format(len(bg)))
    ft = [tokens(p, ignored) for p in favs]
    bt = [tokens(p, ignored) for p in bg]
    weights, n_fav = train(ft, bt)
    bg_scores = sorted(score_tokens(t, weights) for t in bt)
    fav_scores = sorted(taste_score(t, weights) for t in ft)
    artists = sorted(((n_fav[t] * w, t[2:]) for t, w in weights.items() if t[0] == "a" and w > 0 and n_fav[t] >= 3), reverse=True)
    profile = {"weights": {k: round(v, 3) for k, v in weights.items()}, "bg_scores": [round(x, 3) for x in bg_scores],
               "fav_scores": [round(x, 3) for x in fav_scores],
               "n_fav": len(favs), "n_bg": len(bg), "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "top_artists": [a for _score, a in artists[:30]],
               "fav_artists": sorted({t[2:] for t in n_fav if t[0] == "a"}),
               "fav_ids": [p["id"] for p in favs if p.get("id")],
               "ignored": sorted(ignored)}
    store.save_profile(profile)
    return profile


def period_range(name, today=None):
    t = today or date.today()
    first = t.replace(day=1)
    if name == _("этот месяц"):
        return first, t
    if name == _("прошлый месяц"):
        last = first - timedelta(days=1)
        return last.replace(day=1), last
    if name == _("последние 3 месяца"):
        return t - timedelta(days=90), t
    if name == _("этот год"):
        return date(t.year, 1, 1), t
    if name == _("прошлый год"):
        return date(t.year - 1, 1, 1), date(t.year - 1, 12, 31)
    return None


def clean_tag(text: str) -> str:
    return "_".join((text or "").strip().lower().split())


def taste_seeds(profile, blocked=(), round_no=1) -> list:
    """Что искать для «Для вас»: понемногу из каждого вида признаков. Каждый новый заход берёт следующие."""
    weights, seeds = profile["weights"], []
    for kind, n in SEED_MIX:
        top = sorted((t for t, v in weights.items() if t[0] == kind and v > 0 and t not in blocked), key=lambda t: (-weights[t], t))
        seeds += [t[2:] for t in top[(round_no - 1) * n:round_no * n]]
    return seeds


def fetch_for_you(services, store, profile, page, state):
    """Популярное за неделю плюс лучшее из недавнего по признакам вкуса. Один неудачный запрос ленту не ломает."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    posts, last, jobs = [], None, [lambda: get_posts(services, store, POPULAR_PATH, {"date": yesterday, "scale": "week"},
                                                     per_page=POPULAR_PER_PAGE, first_page=page)]
    for tag in (taste_seeds(profile, store.blocked(), page) if profile else []):
        age = f"age:<{FOR_YOU_DAYS}d"
        variants = [f"{tag} {age} order:score", f"{tag} {age}", tag]
        jobs.append(lambda v=variants: get_posts_fallback(services, store, v, state, per_page=FOR_YOU_PER_SEED))
    return run_jobs(jobs)


def run_jobs(jobs):
    """Запросы одного захода: неудача одного не ломает остальные, ошибка выходит наружу, только если не удалось ничего."""
    posts, last = [], None
    for job in jobs:
        try:
            posts += job()
        except Exception as e:
            log.warning("Запрос ленты не удался: %s", e)
            last = e
    if not posts and last is not None:
        raise last
    return posts


def pick_months(first_year, last_year, used, rng, n=TIME_MONTHS, today=None):
    """Случайные месяцы, разнесённые по всему промежутку лет: по одному из n равных частей. Будущее не берём.
    Возвращает (месяцы «ГГГГ-ММ», новый список посещённых); когда непосещённых не хватает, круг начинается заново."""
    t = today or date.today()
    months = [f"{y:04d}-{m:02d}" for y in range(first_year, last_year + 1) for m in range(1, 13) if (y, m) < (t.year, t.month)]
    fresh = [m for m in months if m not in used]
    if len(fresh) < n:
        fresh, used = months, set()
    n = min(n, len(fresh))
    picked = [rng.choice(fresh[i * len(fresh) // n:(i + 1) * len(fresh) // n]) for i in range(n)]
    return picked, sorted(set(used) | set(picked))


def month_range(month: str):
    start = date.fromisoformat(month + "-01")
    return start, (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def fetch_time(services, store, profile, months, state):
    """Лучшее за каждый месяц (один запрос без тегов, работает на любом аккаунте) плюс находки по вкусу за тот же месяц."""
    rng = random.Random(",".join(months))
    seeds = []
    if profile:
        blocked = store.blocked()
        seeds = taste_seeds(profile, blocked, 1) + taste_seeds(profile, blocked, 2)
    jobs = []
    for month in months:
        start, end = month_range(month)
        jobs.append(lambda d=start.isoformat(): get_posts(services, store, POPULAR_PATH, {"date": d, "scale": "month"},
                                                          per_page=TIME_PER_MONTH))
        span = f"date:{start.isoformat()}..{end.isoformat()}"
        for tag in rng.sample(seeds, min(TIME_SEEDS, len(seeds))):
            jobs.append(lambda v=(f"{tag} {span} order:score", f"{tag} {span}"):
                        get_posts_fallback(services, store, v, state, per_page=TIME_PER_SEED))
    return run_jobs(jobs)


def fetch_candidates(services, store, source, opts, profile, refresh=False):
    """Возвращает (кандидаты, из_кэша). Кэш живёт CACHE_HOURS часов: повторный просмотр не тратит запросов."""
    tag = clean_tag(opts.get("tag"))
    page, pages = opts.get("page", 1), opts.get("pages", 2)
    key = json.dumps([source, opts.get("scale"), opts.get("period"), tag, pages, opts.get("n_artists"), opts.get("days"),
                      page, bool(profile), opts.get("months"), date.today().isoformat()], ensure_ascii=False)
    if not refresh:
        hit = store.qcache_get(key, CACHE_HOURS)
        if hit is not None:
            return hit, True
    posts = []
    state = {}                 # какой вариант запроса принял сайт (см. get_posts_fallback)
    services.last_note = ""
    first = (page - 1) * pages + 1
    if source == SRC_FOR_YOU:
        posts = fetch_for_you(services, store, profile, page, state)
    elif source == SRC_TIME:
        if not opts.get("months"):
            raise ValueError(_("В выбранных годах нет прошедших месяцев"))
        posts = fetch_time(services, store, profile, opts["months"], state)
    elif source == SRC_POPULAR:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        posts = get_posts(services, store, POPULAR_PATH, {"date": yesterday, "scale": POP_SCALES.get(opts.get("scale"), "month")},
                          per_page=POPULAR_PER_PAGE, first_page=page)
    elif source == SRC_BEST:
        if not tag:
            raise ValueError(_("Введите тег или имя автора"))
        rng = period_range(opts.get("period"))
        if rng:
            span = f"date:{rng[0].isoformat()}..{rng[1].isoformat()}"
            variants = [f"{tag} {span} order:score", f"{tag} {span}", f"{tag} order:score", tag]
        else:
            variants = [f"{tag} order:score", tag]
        posts = get_posts_fallback(services, store, variants, state, pages=pages, first_page=first)
    elif source == SRC_NEW:
        if not tag:
            raise ValueError(_("Введите тег или имя автора"))
        days = opts.get("days", 30)
        variants = [f"{tag} age:<{days}d", tag] if days else [tag]
        posts = get_posts_fallback(services, store, variants, state, pages=pages, first_page=first)
    elif source == SRC_ARTISTS:
        if not profile or not profile.get("top_artists"):
            raise ValueError(_("Сначала постройте профиль вкуса: в нём берутся ваши любимые авторы"))
        n = opts.get("n_artists", 10)
        for artist in profile["top_artists"][(page - 1) * n:page * n]:
            posts += get_posts_fallback(services, store, [f"{artist} age:<30d order:score", f"{artist} age:<30d"], state,
                                        per_page=15)
    seen, out = set(), []
    for p in posts:
        s = slim(p)
        if s["id"] and s["id"] not in seen:
            seen.add(s["id"])
            out.append(s)
    store.qcache_set(key, out)
    if state.get("simplified"):
        services.last_note = (_("сайт принял только упрощённый запрос (ограничение вашего типа аккаунта): "
                              "список собран без части условий, сортировка по очкам выполняется у вас"))
    return out, False


# ============================ ранжирование и фильтры ============================

def rank_and_filter(cands, ctx):
    """
    ctx: profile, fav_ids, blocked, seen (словарь id->состояние), ratings, min_score, max_per_artist,
         only_new_authors, show_skipped, sort, rng, signals (решения в ленте), shown (что уже показывали),
         quality (вес очков сайта: у старых постов очков меньше, «Машина времени» его выключает).
    Возвращает (видимые карточки, статистика отсева).
    """
    profile = ctx.get("profile")
    weights = learned_weights(profile["weights"] if profile else {}, ctx.get("signals") or {})
    fav_scores = profile.get("fav_scores") if profile else None
    bg_scores = profile["bg_scores"] if profile else []
    shown = ctx.get("shown") or {}
    ignored = set(profile["ignored"]) if profile else set()
    fav_artists = set(profile["fav_artists"]) if profile else set()
    stats = Counter()
    pool = []
    for p in cands:
        pid = p["id"]
        if pid in ctx["fav_ids"] or ctx["seen"].get(pid) == "added":
            stats[_("уже в Favorites")] += 1
            continue
        if ctx["seen"].get(pid) == "skipped" and not ctx.get("show_skipped"):
            stats[_("пропущено вами")] += 1
            continue
        if not p.get("preview"):                      # сайт скрыл файл: показывать нечего
            stats[_("нет миниатюры")] += 1
            continue
        if p["rating"] not in ctx["ratings"]:
            stats[_("рейтинг")] += 1
            continue
        if p["score"] < ctx.get("min_score", 0):
            stats[_("мало очков")] += 1
            continue
        toks = tokens(p, ignored)
        if ctx["blocked"] and any(t in ctx["blocked"] for t in toks):
            stats[_("скрыто вами")] += 1
            continue
        artists = p["a"].split()
        if ctx.get("only_new_authors") and any(a in fav_artists for a in artists):
            stats[_("знакомый автор")] += 1
            continue
        item = dict(p)
        item["toks"] = toks
        s = taste_score(toks, weights)
        item["rank"] = s + ctx.get("quality", QUALITY_WEIGHT) * math.log1p(max(p["score"], 0)) - SHOWN_PENALTY * min(shown.get(pid, 0), 3)
        if not profile:
            item["match"] = None
        elif fav_scores:
            item["match"] = match_percent(s, fav_scores)
        else:                                         # профиль старой версии: сравнение только с обычными постами
            item["match"] = match_percent(score_tokens(toks, weights), bg_scores)
        item["pos"], item["neg"] = explain(toks, weights)
        item["new_author"] = bool(profile and artists and not any(a in fav_artists for a in artists))
        pool.append(item)
    sort = ctx.get("sort", SORTS[0])
    if sort == SORTS[0] and weights:
        pool.sort(key=lambda x: (-x["rank"], -x["score"]))
        pool = diversify(pool)
    elif sort == SORTS[2]:
        pool.sort(key=lambda x: -x["fav_count"])
    elif sort == SORTS[3]:
        pool.sort(key=lambda x: -x["id"])
    elif sort == SORTS[4]:
        ctx["rng"].shuffle(pool)
    else:
        pool.sort(key=lambda x: -x["score"])
    cap = ctx.get("max_per_artist", 0)
    if cap:
        counts, kept = Counter(), []
        for item in pool:
            first = item["a"].split()[0] if item["a"] else None
            if first and counts[first] >= cap:
                stats[_("лишнее от одного автора")] += 1
                continue
            if first:
                counts[first] += 1
            kept.append(item)
        pool = kept
    return pool, stats


# ============================ кэш картинок ============================

def prune_cache(folder: Path, max_mb: int):
    """Хранит не больше max_mb: самые старые файлы удаляются первыми."""
    if not folder.exists():
        return
    files = sorted(((f.stat().st_mtime, f.stat().st_size, f) for f in folder.iterdir() if f.is_file()))
    total = sum(s for _name, s, _x in files)
    limit = max_mb * 1024 * 1024
    if total <= limit:
        return
    for _name, size, f in files:
        if total <= limit * 0.8:
            break
        try:
            f.unlink()
            total -= size
        except OSError:
            pass


def large_urls(preview_url: str):
    """Адреса картинки покрупнее миниатюры (720 px, потом 360 px), вместо 1-2 МБ «среднего размера»."""
    urls = []
    if "/180x180/" in preview_url:
        stem = preview_url.replace("/180x180/", "/720x720/").rsplit(".", 1)[0]
        urls += [stem + ".webp", stem + ".jpg", preview_url.replace("/180x180/", "/360x360/")]
    urls.append(preview_url)
    out = []
    for u in urls:
        if u and u not in out:
            out.append(u)
    return out


# ============================ окно ============================

class BrowseWindow:
    """
    services - связь с программой (см. BrowseServices в danbooru_library_master.py):
      username, base_url, cache_dir, api_json(path, params)->(данные, байты), add_favorite(id),
      favorite_ids(), ignored_tags(), ignore_tags(tags).
    """

    def __init__(self, win, services, auto_load=True):
        self.win = win
        self.sv = services
        self.store = Store(Path(services.cache_dir) / "browse.db")
        self.http = requests.Session()
        self.http.headers["User-Agent"] = "DanbooruLibraryMaster/browse"
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.q = queue.Queue()
        self.alive = True
        self.busy = False
        self.profile = self.store.load_profile()
        self.fav_ids = set(self.sv.favorite_ids()) | set((self.profile or {}).get("fav_ids", []))
        self.cands, self.visible, self.cards, self.photos = [], [], {}, {}
        self.selected, self.cursor = set(), None
        self.page, self.undo, self.shuffle_seed, self.months = 1, [], random.random(), []
        self.shown_before = self.store.shown_map()     # снимок на всю сессию: порядок не прыгает, пока вы смотрите
        self.dev_shown = developer_mode()
        self.preview_win, self.preview_img, self.preview_pid = None, None, None
        self.last_stats = Counter()
        self.thumb_dir, self.large_dir = Path(services.cache_dir) / "thumbs", Path(services.cache_dir) / "large"
        for d in (self.thumb_dir, self.large_dir):
            d.mkdir(parents=True, exist_ok=True)
        prune_cache(self.thumb_dir, THUMB_CACHE_MB)
        prune_cache(self.large_dir, THUMB_CACHE_MB)

        win.title(_("Обзор: лента рекомендаций"))
        app_paths.set_window_icon(win)
        win.geometry("1180x820")
        win.configure(bg=BG)
        self.build_controls()
        self.build_grid()
        self.build_actions()
        win.bind("<Key>", self.on_key)
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.after(50, self.poll)
        self.update_banner()
        self.apply_developer_mode()
        if auto_load:
            self.win.after(100, self.auto_start)

    # ---------- построение окна ----------
    def make_button(self, parent, text, command, color=GREY, **kw):
        b = tk.Button(parent, text=text, command=command, bg=color, fg="white", activebackground=color, activeforeground="white",
                      relief="flat", takefocus=0, padx=8, pady=3, **kw)
        b.pack(side="left", padx=3)
        return b

    def build_controls(self):
        top = tk.Frame(self.win, bg=BG2)
        top.pack(fill="x")
        r1 = tk.Frame(top, bg=BG2)
        r1.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(r1, text=_("Источник:"), bg=BG2, fg=FG).pack(side="left")
        self.var_source = tk.StringVar(value=SRC_FOR_YOU)
        self.cmb_source = ttk.Combobox(r1, textvariable=self.var_source, values=SOURCES, state="readonly", width=30, takefocus=0)
        self.cmb_source.pack(side="left", padx=4)
        self.cmb_source.bind("<<ComboboxSelected>>", lambda e: self.on_source_changed())
        self.var_scale = tk.StringVar(value=_("за месяц"))
        self.cmb_scale = ttk.Combobox(r1, textvariable=self.var_scale, values=list(POP_SCALES), state="readonly", width=10, takefocus=0)
        self.cmb_scale.bind("<<ComboboxSelected>>", lambda e: (self.start_load(False), self.focus_grid()))
        self.var_period = tk.StringVar(value=PERIODS[0])
        self.cmb_period = ttk.Combobox(r1, textvariable=self.var_period, values=PERIODS, state="readonly", width=18, takefocus=0)
        self.var_tag = tk.StringVar()
        self.cmb_tag = ttk.Combobox(r1, textvariable=self.var_tag, width=26, values=[])
        self.cmb_tag.bind("<KeyRelease>", self.on_tag_typed)
        self.cmb_tag.bind("<Return>", lambda e: (self.start_load(False), self.focus_grid()))
        self.lbl_tag = tk.Label(r1, text=_("тег/автор:"), bg=BG2, fg=FG)
        self.lbl_period = tk.Label(r1, text=_("период:"), bg=BG2, fg=FG)
        this_year = date.today().year
        saved_years = (self.store.get_meta("time_years") or f"{FIRST_YEAR + 3},{this_year - 1}").split(",")
        self.lbl_years = tk.Label(r1, text=_("годы:"), bg=BG2, fg=FG)
        self.lbl_dash = tk.Label(r1, text="–", bg=BG2, fg=FG)
        self.spin_from, self.spin_to = (tk.Spinbox(r1, from_=FIRST_YEAR, to=this_year, width=5) for _i in range(2))
        for spin, value in zip((self.spin_from, self.spin_to), saved_years):
            spin.delete(0, "end")
            spin.insert(0, value)
            spin.bind("<Return>", lambda e: (self.start_load(False), self.focus_grid()))
        self.btn_load = self.make_button(r1, _("Загрузить"), lambda: self.start_load(False), GREEN, font=("Arial", 10, "bold"))
        self.btn_refresh = self.make_button(r1, _("Обновить с сайта"), lambda: self.start_load(True))
        self.make_button(r1, _("Фильтры…"), self.toggle_filters)
        self.make_button(r1, _("Мой вкус…"), self.show_profile, TEAL)
        self.make_button(r1, _("Скрытое…"), self.show_blocked)

        self.filters = tk.Frame(top, bg=BG2)           # свёрнуто: лента должна работать без настройки
        r2 = tk.Frame(self.filters, bg=BG2)
        r2.pack(fill="x", padx=6, pady=(2, 6))
        tk.Label(r2, text=_("Сортировка:"), bg=BG2, fg=FG).pack(side="left")
        self.var_sort = tk.StringVar(value=SORTS[0])
        cmb = ttk.Combobox(r2, textvariable=self.var_sort, values=SORTS, state="readonly", width=28, takefocus=0)
        cmb.pack(side="left", padx=4)
        cmb.bind("<<ComboboxSelected>>", lambda e: (self.new_shuffle(), self.refilter(), self.focus_grid()))
        tk.Label(r2, text=_("Рейтинг:"), bg=BG2, fg=FG).pack(side="left", padx=(10, 2))
        self.var_rating = {}
        saved_ratings = load_saved_ratings()           # по умолчанию показываем всё; выбор запоминается
        for r in RATING_ORDER:
            v = tk.BooleanVar(value=r in saved_ratings)
            self.var_rating[r] = v
            tk.Checkbutton(r2, text=r, variable=v, bg=BG2, fg=FG, selectcolor=BG, activebackground=BG2, activeforeground=FG,
                           takefocus=0, command=lambda: (save_ratings({k for k, x in self.var_rating.items() if x.get()}),
                                                         self.refilter())).pack(side="left")
        tk.Label(r2, text=_("очки ≥"), bg=BG2, fg=FG).pack(side="left", padx=(10, 2))
        self.spin_score = tk.Spinbox(r2, from_=0, to=5000, increment=5, width=5, command=self.refilter)
        self.spin_score.delete(0, "end")
        self.spin_score.insert(0, "0")
        self.spin_score.pack(side="left")
        self.spin_score.bind("<Return>", lambda e: (self.refilter(), self.focus_grid()))
        tk.Label(r2, text=_("не больше от автора:"), bg=BG2, fg=FG).pack(side="left", padx=(10, 2))
        self.spin_cap = tk.Spinbox(r2, from_=0, to=50, width=3, command=self.refilter)
        self.spin_cap.delete(0, "end")
        self.spin_cap.insert(0, "3")
        self.spin_cap.pack(side="left")
        self.spin_cap.bind("<Return>", lambda e: (self.refilter(), self.focus_grid()))
        r3 = tk.Frame(self.filters, bg=BG2)
        r3.pack(fill="x", padx=6, pady=(0, 6))
        self.var_new = tk.BooleanVar(value=False)
        self.var_skipped = tk.BooleanVar(value=False)
        for var, text in ((self.var_new, _("только новые для меня авторы")), (self.var_skipped, _("показывать пропущенные мной"))):
            tk.Checkbutton(r3, text=text, variable=var, bg=BG2, fg=FG, selectcolor=BG, activebackground=BG2, activeforeground=FG,
                           takefocus=0, command=self.refilter).pack(side="left", padx=(0, 14))
        tk.Label(r3, text=_("Ctrl+клик: выбрать несколько, пробел: крупно, F: в Favorites, X: пропустить, B: скрыть автора"),
                 bg=BG2, fg=MUTED, font=("Arial", 9)).pack(side="right")
        if saved_ratings != set(RATING_ORDER):         # суженный выбор не должен быть незаметным
            self.filters.pack(fill="x")
        self.update_source_widgets()

    def toggle_filters(self):
        if self.filters.winfo_manager():
            self.filters.pack_forget()
        else:
            self.filters.pack(fill="x")

    def apply_developer_mode(self):
        self.dev_shown = developer_mode()
        if self.dev_shown:
            self.btn_refresh.pack(side="left", padx=3, after=self.btn_load)
        else:
            self.btn_refresh.pack_forget()
        self.update_status()
        self.show_detail()

    def on_source_changed(self):
        self.update_source_widgets()
        self.focus_grid()
        if self.var_source.get() not in (SRC_BEST, SRC_NEW):      # там нужен тег: загрузка по кнопке
            self.start_load(False)

    def auto_start(self):
        if self.alive:
            self.start_load(False)

    def update_source_widgets(self):
        for w in (self.cmb_scale, self.lbl_tag, self.cmb_tag, self.lbl_period, self.cmb_period, self.lbl_years, self.spin_from,
                  self.lbl_dash, self.spin_to):
            w.pack_forget()
        src = self.var_source.get()
        anchor = {"before": self.btn_load}
        if src == SRC_TIME:
            self.lbl_years.pack(side="left", padx=(10, 2), **anchor)
            for w in (self.spin_from, self.lbl_dash, self.spin_to):
                w.pack(side="left", **anchor)
        elif src == SRC_POPULAR:
            self.cmb_scale.pack(side="left", padx=4, **anchor)
        elif src in (SRC_BEST, SRC_NEW):
            self.lbl_tag.pack(side="left", padx=(10, 2), **anchor)
            self.cmb_tag.pack(side="left", **anchor)
            if src == SRC_BEST:
                self.lbl_period.pack(side="left", padx=(8, 2), **anchor)
                self.cmb_period.pack(side="left", **anchor)

    def build_grid(self):
        self.banner = tk.Frame(self.win, bg="#263238")
        tk.Label(self.banner, text=_("Сейчас лента общая. Настройте её по вашему избранному: это около минуты, "
                                     "а дальше она учится на каждом вашем решении."),
                 bg="#263238", fg=FG, wraplength=860, justify="left").pack(side="left", padx=8, pady=6)
        self.make_button(self.banner, _("Настроить под мой вкус"), self.start_profile, GREEN).pack(side="right", padx=8)
        self.mid = mid = tk.Frame(self.win, bg=BG)
        mid.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(mid, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.blank = tk.PhotoImage(width=THUMB, height=THUMB)
        self.canvas.bind("<Configure>", lambda e: self.relayout())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.lbl_empty = tk.Label(self.inner, text="", bg=BG, fg=MUTED, font=("Arial", 13), justify="center")

    def build_actions(self):
        bar = tk.Frame(self.win, bg=BG2)
        bar.pack(fill="x", side="bottom")
        self.lbl_detail = tk.Label(bar, text="", bg=BG2, fg=FG, anchor="w", justify="left", font=("Arial", 10), wraplength=1100)
        self.lbl_detail.pack(fill="x", padx=8, pady=(6, 2))
        row = tk.Frame(bar, bg=BG2)
        row.pack(fill="x", padx=6, pady=4)
        self.make_button(row, _("Открыть на сайте (O)"), self.act_open_site, TEAL)
        self.make_button(row, _("В Favorites (F)"), self.act_favorite, GREEN, font=("Arial", 10, "bold"))
        self.make_button(row, _("Пропустить (X)"), self.act_skip)
        self.make_button(row, _("Вернуть (Z)"), self.act_undo)
        self.make_button(row, _("Скрыть автора (B)"), self.act_block_author, ORANGE)
        self.make_button(row, _("Скрыть тег…"), self.act_block_tag, ORANGE)
        self.make_button(row, _("Крупно (Пробел)"), self.act_preview)
        self.make_button(row, _("Выбрать все"), self.select_all)
        self.make_button(row, _("Показать ещё"), lambda: self.start_load(False, more=True), GREEN)
        self.lbl_status = tk.Label(bar, text="", bg=BG2, fg=MUTED, anchor="w", font=("Arial", 9))
        self.lbl_status.pack(fill="x", padx=8, pady=(0, 6))

    # ---------- очередь событий и фоновые задачи ----------
    def ui(self, fn, *args):
        self.q.put((fn, args))

    def poll(self):
        if not self.alive:
            return
        if self.dev_shown != developer_mode():         # переключатель в «О программе» главного окна
            self.dev_shown = developer_mode()
            self.ui(self.apply_developer_mode)
        try:
            while True:
                fn, args = self.q.get_nowait()
                try:
                    fn(*args)
                except tk.TclError:
                    pass
        except queue.Empty:
            pass
        try:
            self.win.after(50, self.poll)
        except tk.TclError:
            pass

    def run_bg(self, work, done, busy=True):
        if busy:
            self.busy = True
            self.btn_load.config(state="disabled")

        def runner():
            try:
                result, error = work(), None
            except Exception as e:
                log.warning("Ошибка в фоновой задаче ленты: %s", e, exc_info=True)
                result, error = None, e
            self.ui(self.finish_bg, done, result, error, busy)

        threading.Thread(target=runner, daemon=True).start()

    def finish_bg(self, done, result, error, busy):
        if busy:
            self.busy = False
            self.btn_load.config(state="normal")
        done(result, error)

    def set_status(self, text):
        self.lbl_status.config(text=text)

    def update_status(self, extra=""):
        parts = [_("Показано: {0}").format(len(self.visible))]
        if developer_mode():
            req, nbytes = self.store.traffic_today()
            stats = ", ".join(f"{k}: {v}" for k, v in self.last_stats.items() if v)
            parts = [_("Сегодня запросов: {0}, трафик: {1:.1f} МБ").format(req, nbytes / 1048576),
                     _("кандидатов: {0}, показано: {1}").format(len(self.cands), len(self.visible))]
            if stats:
                parts.append(_("скрыто ({0})").format(stats))
        if extra:
            parts.insert(0, extra)
        self.set_status("   |   ".join(parts))

    def focus_grid(self):
        try:
            self.canvas.focus_set()
        except tk.TclError:
            pass

    # ---------- профиль ----------
    def update_banner(self):
        if self.profile is None:
            self.banner.pack(fill="x", before=self.mid)
        else:
            self.banner.pack_forget()

    def start_profile(self):
        if self.busy:
            return
        self.set_status(_("Строю профиль вкуса…"))

        def work():
            return build_profile(self.sv, self.store, lambda t: self.ui(self.set_status, t))

        self.run_bg(work, self.profile_done)

    def profile_done(self, profile, error):
        if error:
            self.set_status(_("Профиль не построен: {0}").format(error))
            messagebox.showerror(_("Профиль"), _("Не удалось построить профиль:\n{0}").format(error), parent=self.win)
            return
        self.profile = profile
        self.fav_ids |= set(profile.get("fav_ids", []))
        self.update_banner()
        self.refilter(note=_("Профиль готов"))
        if self.var_source.get() == SRC_FOR_YOU:
            self.start_load(False)

    def show_profile(self):
        win = tk.Toplevel(self.win)
        win.title(_("Профиль вкуса"))
        win.geometry("640x520")
        win.configure(bg=BG)
        p, dev = self.profile, developer_mode()
        if p is None:
            text = _("Вкус ещё не настроен: лента учится только на ваших решениях.")
        else:
            w = p["weights"]
            tops = {}
            kinds = [("a", _("Авторы")), ("c", _("Персонажи")), ("s", _("Серии")), ("t", _("Теги"))]
            for kind, name in kinds + ([("r", _("Рейтинг"))] if dev else []):
                items = sorted(((v * MULT[k[0]], k[2:]) for k, v in w.items() if k[0] == kind and v > 0), reverse=True)[:10]
                tops[name] = ", ".join(f"{n} ({c:.1f})" if dev else n for c, n in items) or "-"
            sections = "\n\n".join(f"{k}:\n{v}" for k, v in tops.items())
            if dev:
                neg = sorted(((v * MULT[k[0]], k) for k, v in w.items() if v < 0))[:12]
                text = (_("Построен: {0}\nИзбранных учтено: {1}, фон для сравнения: {2} постов\nПризнаков с весом: {3}\n\n").format(p['built'], p['n_fav'], p['n_bg'], len(w)) + sections +
                        _("\n\nМинусовые (чего вы избегаете):\n") + (", ".join(f"{describe(t)} ({c:.1f})" for c, t in neg) or "-"))
            else:
                text = _("Учтено ваших избранных: {0}, обновлено {1}. Лента сразу учитывает и ваши решения в ней.\n\n").format(p['n_fav'], p['built']) + sections
        box = tk.Text(win, bg="#222222", fg=FG, wrap="word", relief="flat")
        box.insert("1.0", text)
        box.config(state="disabled")
        box.pack(fill="both", expand=True, padx=8, pady=8)
        self.make_button(win, _("Обновить профиль (≈35 запросов)") if dev else _("Обновить мой вкус"),
                         lambda: (win.destroy(), self.start_profile()), GREEN)

    # ---------- загрузка кандидатов ----------
    def on_tag_typed(self, event):
        text = clean_tag(self.var_tag.get())
        if len(text) < 3 or getattr(self, "_suggesting", False) or event.keysym in ("Return", "Up", "Down", "Left", "Right"):
            return
        self._suggesting = True

        def work():
            data = api(self.sv, self.store, "/tags.json", {"search[name_matches]": text + "*", "search[order]": "count", "limit": 8})
            return [f"{t.get('name')}" for t in data if t.get("name")]

        def done(result, error):
            self._suggesting = False
            if result:
                self.cmb_tag.config(values=result)

        self.run_bg(work, done, busy=False)

    def current_opts(self):
        return {"scale": self.var_scale.get(), "period": self.var_period.get(), "tag": self.var_tag.get(), "pages": 2,
                "n_artists": 10, "days": 30}

    def start_load(self, refresh, more=False):
        if self.busy:
            return
        page = self.page + 1 if more else 1
        source, opts = self.var_source.get(), dict(self.current_opts(), page=page)
        if source == SRC_TIME:                         # каждая загрузка - новые месяцы
            opts["months"] = self.months = self.roll_months()
        self.set_status(_("Загружаю список…"))
        if not self.visible:
            self.show_message(_("Загружаю список…"))

        def work():
            return fetch_candidates(self.sv, self.store, source, opts, self.profile, refresh)

        self.run_bg(work, lambda result, error: self.load_done(result, error, more, page))

    def time_years(self):
        now = date.today().year
        try:
            years = sorted(max(FIRST_YEAR, min(now, int(s.get()))) for s in (self.spin_from, self.spin_to))
        except ValueError:
            years = [FIRST_YEAR + 3, now - 1]
        return years

    def roll_months(self):
        first, last = self.time_years()
        self.store.set_meta("time_years", f"{first},{last}")
        used = json.loads(self.store.get_meta("time_months", "[]"))
        months, used = pick_months(first, last, set(used), random.Random())
        self.store.set_meta("time_months", json.dumps(used))
        return months

    def load_done(self, result, error, more=False, page=1):
        if error:
            self.set_status(_("Не удалось загрузить: {0}").format(error))
            if not more:
                self.show_message(_("Не удалось загрузить список.\n{0}").format(error))
            return
        cands, from_cache = result
        extra = getattr(self.sv, "last_note", "")
        if developer_mode():
            note = _("из кэша, без запросов") if from_cache else (_("загружено с сайта; ") + extra if extra else _("загружено с сайта"))
        else:
            note = extra
        if self.months and self.var_source.get() == SRC_TIME:
            shown_months = _("Месяцы: {0}").format(", ".join(sorted(self.months)))
            note = f"{shown_months}; {note}" if note else shown_months
        self.page = page
        if more:
            self.append_posts(cands, note)
            return
        self.cands = cands
        self.new_shuffle()
        self.refilter(note=note)
        self.store.mark_shown([v["id"] for v in self.visible[:SHOWN_TOP]])

    def append_posts(self, cands, note):
        """«Показать ещё»: новое идёт в конец, то, что уже на экране, не перемешивается."""
        known = {c["id"] for c in self.cands}
        fresh = [c for c in cands if c["id"] not in known]
        if not fresh:
            self.update_status(_("Новых постов больше нет"))
            return
        self.cands += fresh
        ranked, stats = rank_and_filter(fresh, self.current_ctx())
        self.last_stats.update(stats)
        if ranked and not self.cards:                  # убираем сообщение «всё разобрано»
            for w in self.inner.winfo_children():
                w.destroy()
        self.visible += ranked
        for item in ranked:
            self.cards[item["id"]] = self.make_card(item)
            self.pool.submit(self.load_thumb, item)
        self.relayout()
        self.store.mark_shown([v["id"] for v in ranked[:SHOWN_TOP]])
        self.update_status(note)

    # ---------- фильтры и сетка ----------
    def current_ctx(self):
        try:
            min_score = int(self.spin_score.get())
        except ValueError:
            min_score = 0
        try:
            cap = int(self.spin_cap.get())
        except ValueError:
            cap = 0
        return {"profile": self.profile, "fav_ids": self.fav_ids, "blocked": self.store.blocked(), "seen": self.store.seen_map(),
                "ratings": {r for r, v in self.var_rating.items() if v.get()}, "min_score": min_score, "max_per_artist": cap,
                "only_new_authors": self.var_new.get(), "show_skipped": self.var_skipped.get(), "sort": self.var_sort.get(),
                "rng": random.Random(self.shuffle_seed), "signals": self.store.signals(), "shown": self.shown_before,
                "quality": 0.0 if self.var_source.get() == SRC_TIME else QUALITY_WEIGHT}

    def new_shuffle(self):
        self.shuffle_seed = random.random()

    def refilter(self, note=""):
        visible, self.last_stats = rank_and_filter(self.cands, self.current_ctx())
        keep = {i for i in self.selected if any(v["id"] == i for v in visible)}
        self.selected = keep
        self.visible = visible
        if self.cursor is not None and not any(v["id"] == self.cursor for v in visible):
            self.cursor = None
        self.rebuild_grid()
        self.update_status(note)
        self.show_detail()

    def show_message(self, text):
        for w in self.inner.winfo_children():
            w.destroy()
        self.cards = {}
        self.lbl_empty = tk.Label(self.inner, text=text, bg=BG, fg=MUTED, font=("Arial", 13), justify="center")
        self.lbl_empty.grid(row=0, column=0, padx=40, pady=60)

    def rebuild_grid(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.cards = {}
        if not self.visible:
            msg = _("Ничего не найдено по этим условиям.") if self.cands else _("Выберите источник и нажмите «Загрузить».")
            if self.cands:
                msg += _("\nПопробуйте ослабить фильтры (рейтинг, очки, «только новые авторы»).")
            self.show_message(msg)
            return
        for item in self.visible:
            self.cards[item["id"]] = self.make_card(item)
        self.relayout()
        self.canvas.yview_moveto(0)
        for item in self.visible:
            self.pool.submit(self.load_thumb, item)

    def make_card(self, item):
        card = tk.Frame(self.inner, bg=BG2, width=CARD_W, height=CARD_H, highlightthickness=3, highlightbackground=BG2)
        card.grid_propagate(False)
        card.pack_propagate(False)
        img = tk.Label(card, image=self.blank, bg="#000000", bd=0)
        img.pack(padx=6, pady=(6, 3))
        match = f"{item['match']:.0f}%" if item["match"] is not None else "-"
        line1 = tk.Label(card, text=f"{match}  {item['rating']}  ★{item['score']}  ♥{item['fav_count']}", bg=BG2, fg=FG, font=("Arial", 9, "bold"))
        line1.pack()
        artist = item["a"].split()[0] if item["a"] else _("(автор не указан)")
        if item["new_author"]:
            line2 = tk.Label(card, text=_("{0} · новый автор").format(artist[:18]), bg=BG2, fg="#4db6ac", font=("Arial", 8))
        else:
            line2 = tk.Label(card, text=artist[:30], bg=BG2, fg=MUTED, font=("Arial", 8))
        line2.pack()
        why = next((describe(t) for t, _w in item["pos"] if t[0] != "r"), "")
        if self.var_source.get() == SRC_TIME and item["created"]:
            why = " · ".join(x for x in (item["created"][:7], why) if x)
        line3 = tk.Label(card, text=why[:32], bg=BG2, fg=MUTED, font=("Arial", 8))
        line3.pack()
        if item["ext"] in ("mp4", "webm", "zip"):
            tk.Label(card, text=_("▶ видео/анимация"), bg=BG2, fg=ORANGE, font=("Arial", 8)).pack()
        for w in (card, img, line1, line2, line3):
            w.bind("<Button-1>", lambda e, pid=item["id"]: self.on_click(pid, e))
            w.bind("<Double-Button-1>", lambda e, pid=item["id"]: (self.on_click(pid, e, True), self.act_preview()))
            w.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            w.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
            w.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        card.img = img
        self.paint_card(item["id"], card)
        return card

    def paint_card(self, pid, card=None):
        card = card or self.cards.get(pid)
        if card is None:
            return
        color = GREEN if pid in self.selected else (TEAL if pid == self.cursor else BG2)
        card.config(highlightbackground=color)

    def relayout(self):
        width = max(self.canvas.winfo_width(), CARD_W + 20)
        cols = max(1, width // (CARD_W + 10))
        for i, item in enumerate(self.visible):
            card = self.cards.get(item["id"])
            if card is not None:
                card.grid(row=i // cols, column=i % cols, padx=4, pady=4)
        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ---------- миниатюры ----------
    def fetch_image(self, url, folder: Path, pid):
        """Возвращает байты картинки из кэша или из сети (в фоновом потоке)."""
        path = folder / f"{pid}.bin"
        if path.exists():
            return path.read_bytes()
        r = self.http.get(url, timeout=30)
        r.raise_for_status()
        path.write_bytes(r.content)
        self.store.add_traffic(1, len(r.content))
        return r.content

    def load_thumb(self, item):
        if not self.alive or not item.get("preview"):
            return
        try:
            from io import BytesIO
            img = Image.open(BytesIO(self.fetch_image(item["preview"], self.thumb_dir, item["id"])))
            img.load()
            img = img.convert("RGB")
            img.thumbnail((THUMB, THUMB))
            canvas = Image.new("RGB", (THUMB, THUMB), (0, 0, 0))
            canvas.paste(img, ((THUMB - img.width) // 2, (THUMB - img.height) // 2))
        except Exception as e:
            log.info("Миниатюра #%s не загрузилась: %s", item["id"], e)
            return
        self.ui(self.set_thumb, item["id"], canvas)

    def set_thumb(self, pid, pil):
        card = self.cards.get(pid)
        if card is None:
            return
        photo = ImageTk.PhotoImage(pil)
        self.photos[pid] = photo
        card.img.config(image=photo)

    # ---------- выбор ----------
    def on_click(self, pid, event=None, force_single=False):
        ctrl = bool(event is not None and (event.state & 0x4)) and not force_single
        if ctrl:
            self.selected ^= {pid}
        else:
            self.selected = {pid}
        old, self.cursor = self.cursor, pid
        for i in {old, pid} | self.selected:
            self.paint_card(i)
        self.show_detail()
        self.focus_grid()

    def select_all(self):
        self.selected = {v["id"] for v in self.visible}
        for pid in self.cards:
            self.paint_card(pid)
        self.show_detail()

    def move(self, delta):
        if not self.visible:
            return
        ids = [v["id"] for v in self.visible]
        idx = (ids.index(self.cursor) + delta) if self.cursor in ids else 0
        idx = max(0, min(len(ids) - 1, idx))
        old, self.cursor, self.selected = self.cursor, ids[idx], {ids[idx]}
        for i in {old, self.cursor} | set(ids[max(0, idx - 2):idx + 3]):
            self.paint_card(i)
        self.show_detail()
        self.scroll_to(self.cursor)
        if self.preview_win is not None and self.preview_win.winfo_exists():
            self.open_preview(self.cursor)

    def scroll_to(self, pid):
        card = self.cards.get(pid)
        if card is None:
            return
        self.inner.update_idletasks()
        total = max(self.inner.winfo_height(), 1)
        top, bottom = card.winfo_y(), card.winfo_y() + CARD_H
        view_top = self.canvas.canvasy(0)
        view_bottom = view_top + self.canvas.winfo_height()
        if top < view_top:
            self.canvas.yview_moveto(top / total)
        elif bottom > view_bottom:
            self.canvas.yview_moveto((bottom - self.canvas.winfo_height()) / total)

    def targets(self):
        ids = [v["id"] for v in self.visible if v["id"] in self.selected]
        if not ids and self.cursor is not None:
            ids = [self.cursor]
        return ids

    def item_by_id(self, pid):
        return next((v for v in self.visible if v["id"] == pid), None)

    def show_detail(self):
        item = self.item_by_id(self.cursor) if self.cursor is not None else None
        if item is None:
            self.lbl_detail.config(text=_("Выберите пост: клик (Ctrl+клик для нескольких) или стрелки."))
            return
        why = ", ".join(describe(t) for t, _w in item["pos"] if t[0] != "r") or _("совпадений с вашим профилем нет")
        minus = (_("   Минусы: ") + ", ".join(describe(t) for t, _w in item["neg"])) if item["neg"] else ""
        match = _("совпадение с вашим вкусом {0:.0f}%").format(item['match']) if item["match"] is not None else _("профиль не построен")
        extra = _("  ({0} выбрано)").format(len(self.selected)) if len(self.selected) > 1 else ""
        if developer_mode():
            self.lbl_detail.config(text=_("#{0}  рейтинг {1}  очки {2}  ♥ {3}  {4}x{5}  {6}   {7}{8}\nПочему: {9}.{10}").format(item['id'], item['rating'], item['score'], item['fav_count'], item['w'], item['h'], item['created'], match, extra, why, minus))
            return
        artist = item["a"].split()[0] if item["a"] else _("(автор не указан)")
        self.lbl_detail.config(text=_("{0}   ★ {1}   ♥ {2}   {3}{4}\nПочему: {5}.{6}").format(artist, item['score'], item['fav_count'], match, extra, why, minus))

    # ---------- действия ----------
    def site_url(self, pid):
        return f"{self.sv.base_url}/posts/{pid}"

    def act_open_site(self):
        for pid in self.targets()[:5]:
            webbrowser.open(self.site_url(pid))

    def remove_cards(self, ids):
        gone = set(ids)
        keep_idx = None
        if self.cursor in gone:
            ids_order = [v["id"] for v in self.visible]
            keep_idx = ids_order.index(self.cursor) if self.cursor in ids_order else 0
        self.visible = [v for v in self.visible if v["id"] not in gone]
        self.selected -= gone
        for pid in gone:
            card = self.cards.pop(pid, None)
            if card is not None:
                card.destroy()
        self.relayout()
        if keep_idx is not None and self.visible:
            nxt = self.visible[min(keep_idx, len(self.visible) - 1)]["id"]
            self.cursor, self.selected = nxt, {nxt}
            self.paint_card(nxt)
        elif not self.visible:
            self.cursor = None
            self.show_message(_("Все посты из этой подборки разобраны. Нажмите «Показать ещё»."))
        self.update_status()
        self.show_detail()

    def act_favorite(self):
        ids = self.targets()
        if not ids or self.busy:
            return
        items = [self.item_by_id(i) for i in ids]
        if len(ids) > 1 and not messagebox.askyesno(_("Добавить в Favorites"), _("Добавить в Favorites постов: {0}?\nЭто изменит ваш аккаунт на Danbooru.").format(len(ids)), parent=self.win):
            return
        self.set_status(_("Добавляю в Favorites: {0}…").format(len(ids)))

        def work():
            done, errors = [], []
            for pid in ids:
                try:
                    self.sv.add_favorite(pid)
                    done.append(pid)
                except Exception as e:
                    log.warning("Не удалось добавить пост #%s в Favorites: %s", pid, e)
                    errors.append(f"#{pid}: {e}")
                    if isinstance(e, PermissionDenied):
                        break
            return done, errors

        def after(result, error):
            if error:
                self.set_status(_("Ошибка: {0}").format(error))
                return
            done, errors = result
            if done:
                self.store.mark_seen(done, "added")
                self.learn([i for i in items if i and i["id"] in done], pos=1)
                self.fav_ids |= set(done)
                self.remove_cards(done)
            if errors:
                messagebox.showerror("Favorites", _("Не удалось добавить:\n") + "\n".join(errors[:5]), parent=self.win)
            self.update_status(_("Добавлено в Favorites: {0}").format(len(done)))

        self.run_bg(work, after, busy=False)

    def learn(self, items, pos=0, neg=0):
        self.store.signal_add([t for item in items for t in item["toks"] if t[0] != "r"], pos, neg)

    def act_skip(self):
        ids = self.targets()
        if ids:
            items = [self.item_by_id(i) for i in ids]
            self.undo.append(items)
            self.learn(items, neg=1)
            self.store.mark_seen(ids, "skipped")
            self.remove_cards(ids)

    def act_undo(self):
        """Вернуть последний пропуск: и пост, и то, чему лента на нём научилась."""
        if not self.undo:
            return
        items = self.undo.pop()
        ids = [i["id"] for i in items]
        self.store.unmark_seen(ids)
        self.learn(items, neg=-1)
        self.cursor, self.selected = ids[0], set(ids)
        self.refilter(note=_("Возвращено: {0}").format(len(ids)))
        self.scroll_to(ids[0])

    def act_block_author(self):
        toks = set()
        for pid in self.targets():
            item = self.item_by_id(pid)
            if item:
                toks |= {f"a:{a}" for a in item["a"].split()}
        if toks:
            self.store.block_add(toks)
            self.refilter(note=_("Скрыто авторов: {0}").format(len(toks)))

    def act_block_tag(self):
        item = self.item_by_id(self.cursor) if self.cursor is not None else None
        if item is None:
            return
        weights = self.profile["weights"] if self.profile else {}
        toks = sorted((t for t in item["toks"] if t[0] in "acst"), key=lambda t: (-abs(weights.get(t, 0) * MULT[t[0]]), t))
        win = tk.Toplevel(self.win)
        win.title(_("Скрыть тег"))
        win.geometry("360x480")
        win.configure(bg=BG)
        tk.Label(win, text=_("Посты с выбранными признаками больше не будут показываться."), bg=BG, fg=FG, wraplength=330).pack(pady=6)
        box = tk.Listbox(win, selectmode="extended", bg="#222222", fg=FG, selectbackground=TEAL)
        box.pack(fill="both", expand=True, padx=8)
        for t in toks:
            box.insert("end", describe(t))

        def apply():
            chosen = {toks[i] for i in box.curselection()}
            if chosen:
                self.store.block_add(chosen)
                win.destroy()
                self.refilter(note=_("Скрыто признаков: {0}").format(len(chosen)))

        self.make_button(win, _("Скрыть выбранные"), apply, ORANGE)

    def show_blocked(self):
        win = tk.Toplevel(self.win)
        win.title(_("Скрытое"))
        win.geometry("360x460")
        win.configure(bg=BG)
        tk.Label(win, text=_("Скрытые авторы и теги. Выделите и нажмите «Вернуть»."), bg=BG, fg=FG, wraplength=330).pack(pady=6)
        box = tk.Listbox(win, selectmode="extended", bg="#222222", fg=FG, selectbackground=TEAL)
        box.pack(fill="both", expand=True, padx=8)
        items = sorted(self.store.blocked())
        for t in items:
            box.insert("end", describe(t))

        def restore():
            chosen = [items[i] for i in box.curselection()]
            if chosen:
                self.store.block_remove(chosen)
                win.destroy()
                self.refilter(note=_("Возвращено: {0}").format(len(chosen)))

        self.make_button(win, _("Вернуть выбранные"), restore, GREEN)

    # ---------- крупный просмотр ----------
    def act_preview(self):
        if self.cursor is not None:
            self.open_preview(self.cursor)

    def open_preview(self, pid):
        item = self.item_by_id(pid)
        if item is None:
            return
        if self.preview_win is None or not self.preview_win.winfo_exists():
            win = tk.Toplevel(self.win)
            win.geometry("900x860")
            win.configure(bg=BG)
            self.preview_win = win
            self.preview_label = tk.Label(win, bg="#000000", fg=MUTED, text=_("Загружаю…"))
            self.preview_label.pack(fill="both", expand=True)
            self.preview_info = tk.Label(win, bg=BG2, fg=FG, anchor="w", justify="left", wraplength=860)
            self.preview_info.pack(fill="x", side="bottom")
            win.bind("<Key>", self.on_key)
            win.bind("<Configure>", lambda e: self.render_preview())
        self.preview_pid, self.preview_img = pid, None
        self.preview_win.title(_("Пост #{0}").format(pid))
        self.preview_label.config(image="", text=_("Загружаю…"))
        self.preview_info.config(text=self.lbl_detail.cget("text"))
        self.pool.submit(self.load_large, item)

    def load_large(self, item):
        from io import BytesIO
        for url in large_urls(item["preview"]):
            try:
                img = Image.open(BytesIO(self.fetch_image(url, self.large_dir, f"{item['id']}_{zlib.crc32(url.encode()) % 10000}")))
                img.load()
                self.ui(self.set_preview, item["id"], img.convert("RGB"))
                return
            except Exception as e:
                log.info("Крупное превью #%s: адрес не подошёл (%s)", item["id"], e)
                continue
        self.ui(self.set_preview, item["id"], None)

    def set_preview(self, pid, pil):
        if pid != self.preview_pid or self.preview_win is None or not self.preview_win.winfo_exists():
            return
        self.preview_img = pil
        if pil is None:
            self.preview_label.config(image="", text=_("Не удалось загрузить картинку"))
        else:
            self.render_preview()

    def render_preview(self):
        if self.preview_img is None or self.preview_win is None or not self.preview_win.winfo_exists():
            return
        w, h = max(self.preview_label.winfo_width(), 200), max(self.preview_label.winfo_height(), 200)
        img = self.preview_img.copy()
        img.thumbnail((w, h))
        self.preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self.preview_photo, text="")

    # ---------- клавиши ----------
    def on_key(self, e):
        try:
            focus = self.win.focus_get()
        except (KeyError, tk.TclError):
            focus = None
        if focus is not None and focus.winfo_class() in TEXT_WIDGETS:
            if e.keysym in ("Return", "KP_Enter", "Escape"):
                self.focus_grid()
            return
        if e.state & 0x4:
            if e.keysym.lower() in ("a", "cyrillic_ef"):
                self.select_all()
                return "break"
            return
        action = KEY_ACTIONS.get(e.keysym) or CHAR_ACTIONS.get((e.char or "").lower())
        if not action:
            return
        {"next": lambda: self.move(1), "prev": lambda: self.move(-1), "preview": self.act_preview,
         "open_site": self.act_open_site, "escape": self.on_escape, "favorite": self.act_favorite,
         "skip": self.act_skip, "undo": self.act_undo, "block_author": self.act_block_author}[action]()
        return "break"

    def on_escape(self):
        if self.preview_win is not None and self.preview_win.winfo_exists():
            self.preview_win.destroy()
        else:
            self.selected = set()
            for pid in self.cards:
                self.paint_card(pid)

    def close(self):
        self.alive = False
        self.pool.shutdown(wait=False, cancel_futures=True)
        try:
            self.store.close()
        except Exception:
            pass
        self.win.destroy()


def main(services):
    """Отдельный запуск окна (ярлык «Обзор постов»)."""
    root = tk.Tk()
    BrowseWindow(root, services)
    root.mainloop()
