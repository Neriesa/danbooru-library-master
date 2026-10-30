# -*- coding: utf-8 -*-
"""Маленький поддельный Danbooru для тестов: профиль, поиск постов, избранное, лимит тегов у бесплатных аккаунтов."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

USERS = {"gold_user": ("goldkey", 30, "Gold"), "free_user": ("freekey", 20, "Member")}
RATINGS = "gsqe"


def make_posts(n=400):
    posts = {}
    for i in range(1, n + 1):
        artist = f"artist_{i % 7}"
        posts[i] = {
            "id": i, "md5": f"{i:032x}", "rating": RATINGS[i % 4], "score": (i * 37) % 120, "fav_count": (i * 11) % 90,
            "is_deleted": i % 50 == 0, "is_banned": False, "file_ext": "jpg",
            "tag_string_artist": artist, "tag_string_character": f"char_{i % 5}", "tag_string_copyright": f"series_{i % 3}",
            "tag_string_general": f"solo tag_{i % 9} tag_{i % 13}", "tag_string_meta": "",
            "tag_string": f"{artist} char_{i % 5} series_{i % 3} solo tag_{i % 9} tag_{i % 13}",
            "file_url": f"/data/{i}.jpg", "large_file_url": f"/data/{i}.jpg", "preview_file_url": f"/data/p{i}.jpg",
            "created_at": "2026-10-01T00:00:00.000+00:00", "up_score": 1, "down_score": 0, "uploader_id": 1, "variants": [],
        }
    return posts


class State:
    def __init__(self):
        self.posts = make_posts()
        self.favs = {"gold_user": set(range(1, 61)), "free_user": set(range(1, 61))}
        self.requests = []          # (method, path, query)
        self.lock = threading.Lock()


def count_tags(q):
    return len([t for t in q.split() if t])


class Handler(BaseHTTPRequestHandler):
    server_version = "MockBooru/1"

    def log_message(self, *a):
        pass

    def _user(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return None
        try:
            name, key = base64.b64decode(h[6:]).decode().split(":", 1)
        except Exception:
            return None
        info = USERS.get(name)
        return (name, info) if info and info[0] == key else None

    def _send(self, code, obj, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        st = self.server.state
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        with st.lock:
            st.requests.append(("GET", u.path, q))
        if u.path.startswith("/data/"):
            body = b"\xff\xd8\xff\xd9"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        me = self._user()
        if me is None:
            return self._send(401, {"success": False, "message": "Authentication failed"})
        name, (_, level, level_string) = me
        if u.path == "/profile.json":
            return self._send(200, {"id": 1, "name": name, "level": level, "level_string": level_string})
        if u.path == "/posts.json":
            return self.posts_json(name, level, q)
        if u.path.startswith("/explore/posts/popular.json"):
            limit_n, page = int(q.get("limit", 20)), int(q.get("page", 1))
            items = sorted(st.posts.values(), key=lambda p: -p["score"])[(page - 1) * limit_n: page * limit_n]
            return self._send(200, items)
        self._send(404, {"success": False, "message": "not found"})

    def posts_json(self, name, level, q):
        st = self.server.state
        tags = q.get("tags", "")
        limit = 6 if level >= 30 else 2
        if count_tags(tags) > limit:
            return self._send(422, {"success": False, "error": "PostQuery::TagLimitError",
                                    "message": f"You cannot search for more than {limit} tags at a time"})
        items = list(st.posts.values())
        order = "id"
        for t in tags.split():
            if t.startswith("md5:"):
                items = [p for p in items if p["md5"] == t[4:]]
            elif t.startswith(("ordfav:", "fav:")):
                items = [p for p in items if p["id"] in st.favs.get(t.split(":", 1)[1], set())]
                if t.startswith("ordfav:"):
                    order = "fav"
            elif t.startswith("id:<"):
                items = [p for p in items if p["id"] < int(t[4:])]
            elif t.startswith("order:score"):
                order = "score"
            elif t.startswith(("status:", "date:", "age:")):
                pass
            elif t.startswith("artist_"):
                items = [p for p in items if p["tag_string_artist"] == t]
            else:
                items = [p for p in items if t in p["tag_string"].split()]
        if not any(t.startswith("status:any") for t in tags.split()):
            items = [p for p in items if not p["is_deleted"]] if "md5:" not in tags else items
        if order == "score":
            items.sort(key=lambda p: -p["score"])
        else:
            items.sort(key=lambda p: -p["id"])
        limit_n, page = int(q.get("limit", 20)), int(q.get("page", 1))
        items = items[(page - 1) * limit_n: page * limit_n]
        only = [f for f in q.get("only", "").split(",") if f]
        if only:
            items = [{k: p[k] for k in only if k in p} for p in items]
        self._send(200, items)

    def do_POST(self):
        st = self.server.state
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode()) if length else {}
        me = self._user()
        if me is None:
            return self._send(401, {"success": False})
        name = me[0]
        with st.lock:
            st.requests.append(("POST", u.path, {k: v[0] for k, v in data.items()}))
        if u.path == "/favorites.json":
            pid = int(data.get("post_id", ["0"])[0])
            if pid in st.favs[name]:
                return self._send(422, {"success": False, "message": "You have already favorited this post"})
            st.favs[name].add(pid)
            return self._send(201, {"id": pid})
        self._send(404, {})

    def do_DELETE(self):
        st = self.server.state
        u = urlparse(self.path)
        me = self._user()
        if me is None:
            return self._send(401, {})
        with st.lock:
            st.requests.append(("DELETE", u.path, {}))
        if u.path.startswith("/favorites/"):
            pid = int(u.path.split("/")[2].split(".")[0])
            st.favs[me[0]].discard(pid)
            return self._send(204, {})
        self._send(404, {})


def start():
    """Запускает сервер на свободном порту. Возвращает (сервер, url, состояние)."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = State()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", srv.state
