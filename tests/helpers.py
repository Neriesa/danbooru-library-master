# -*- coding: utf-8 -*-
import hashlib
import random
from pathlib import Path

from PIL import Image


def say(text, level="info"):
    pass


def progress(done, total, text=""):
    pass


def make_image(path: Path, seed: int, size=(64, 64)) -> str:
    """Картинка из шума: у разных seed разные MD5 и разные pHash. Возвращает MD5."""
    rng = random.Random(seed)
    img = Image.new("RGB", size)
    img.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(size[0] * size[1])])
    img.save(path, "PNG")
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def add_post(state, post_id, md5, deleted=False, rating="g", favorite_of=None):
    base = dict(state.posts[1])
    base.update(id=post_id, md5=md5, is_deleted=deleted, rating=rating, file_ext="png",
                file_url=f"/data/{post_id}.png", large_file_url=f"/data/{post_id}.png")
    state.posts[post_id] = base
    for user in (favorite_of or []):
        state.favs[user].add(post_id)
