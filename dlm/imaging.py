# -*- coding: utf-8 -*-

import warnings
from pathlib import Path

import numpy as np
from PIL import Image

from .constants import IMAGE_EXT, VIDEO_EXT
from .config import log
from .files import calculate_md5, managed_post_id


warnings.filterwarnings("ignore", category=UserWarning, module="PIL.Image")
Image.MAX_IMAGE_PIXELS = 300_000_000


_DCT_N = 32
_DCT = 2.0 * np.cos(np.pi * np.outer(np.arange(_DCT_N), 2 * np.arange(_DCT_N) + 1) / (2 * _DCT_N))


def phash_hex(img: Image.Image) -> str:
    """
    Перцептивный хэш 64 бита (16 hex-цифр). Результат совпадает с imagehash.phash, поэтому хэши,
    посчитанные старыми версиями, остаются действительными; тяжёлые scipy и imagehash не нужны.
    """
    px = np.asarray(img.convert("L").resize((_DCT_N, _DCT_N), Image.LANCZOS), dtype=np.float64)
    low = (_DCT @ px @ _DCT.T)[:8, :8]
    low[np.abs(low) < 1e-6] = 0.0                      # шум округления у однотонных картинок
    bits = (low > np.median(low)).flatten()
    return f"{int(''.join('1' if b else '0' for b in bits), 2):016x}"


def compute_phash(path: Path) -> str:
    """16-значный hex pHash, либо '-' если посчитать нельзя (видео, архив, битый файл)."""
    if path.suffix.lower() not in IMAGE_EXT:
        return "-"
    try:
        with Image.open(path) as img:
            if img.format == "JPEG":
                img.draft("RGB", (512, 512))
            return phash_hex(img)
    except Exception as e:
        log.warning("pHash не посчитан для %s: %s", path, e)
        return "-"


def hash_file(path: Path, root: Path):
    st = path.stat()
    try:
        md5 = calculate_md5(path)
    except OSError as e:
        log.warning("Не удалось прочитать %s: %s", path, e)
        md5 = ""
    phash = compute_phash(path) if md5 else "-"
    pid = managed_post_id(path, root)
    status = "found" if pid else "scanned"
    return (str(path), path.name, st.st_size, st.st_mtime, md5, phash, pid, None, status)


_HAS_CV2 = None


def have_cv2() -> bool:
    """OpenCV нужен только для видео. В облегчённой сборке его нет: видео открываются плеером системы."""
    global _HAS_CV2
    if _HAS_CV2 is None:
        try:
            import cv2  # noqa: F401
            _HAS_CV2 = True
        except ImportError:
            _HAS_CV2 = False
    return _HAS_CV2


def get_resolution(path: Path):
    try:
        ext = path.suffix.lower()
        if ext in IMAGE_EXT:
            with Image.open(path) as img:
                return img.size
        if ext in VIDEO_EXT and have_cv2():
            import cv2
            cap = cv2.VideoCapture(str(path))
            w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return w, h
    except Exception as e:
        log.warning("Разрешение не определено для %s: %s", path, e)
    return 0, 0


def load_preview(path: Path, max_size=(220, 220)):
    try:
        ext = path.suffix.lower()
        if ext in IMAGE_EXT:
            with Image.open(path) as img:
                img.thumbnail(max_size)
                return img.convert("RGB")
        if ext in VIDEO_EXT and have_cv2():
            import cv2
            cap = cv2.VideoCapture(str(path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total > 20:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
            ok, frame = cap.read()
            cap.release()
            if ok:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img.thumbnail(max_size)
                return img
    except Exception as e:
        log.warning("Превью не создано для %s: %s", path, e)
    return None
