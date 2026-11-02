"""Secure image validation + storage. User-supplied filenames are never trusted."""
from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from backend.core.config import settings
from backend.core.exceptions import ImageTooLarge, InvalidImageError, UnsupportedImageFormat

_FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png"}


def validate_image(data: bytes, filename: str | None) -> tuple[str, int, int]:
    """Return (extension, width, height) or raise. Checks type, size, readability, dimensions."""
    cfg = settings()
    ext = Path(filename or "").suffix.lower()
    if ext not in cfg.allowed_extensions:
        raise UnsupportedImageFormat("Unsupported image format. Please upload a JPG, JPEG or PNG file.")
    if len(data) == 0:
        raise InvalidImageError("The uploaded file is empty.")
    if len(data) > cfg.max_upload_bytes:
        raise ImageTooLarge(f"Image is too large. Maximum size is {cfg.max_upload_bytes // (1024 * 1024)} MB.")
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            im.verify()  # structural integrity
        with Image.open(io.BytesIO(data)) as im:
            im.load()  # full decode
            width, height = im.size
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise InvalidImageError("The file is not a readable image.") from None
    if fmt not in _FORMAT_TO_EXT:  # content must really be JPEG/PNG (not just the extension)
        raise UnsupportedImageFormat("Unsupported image content. Please upload a JPG, JPEG or PNG file.")
    if min(width, height) < cfg.min_image_side:
        raise InvalidImageError(f"Image is too small. Minimum side is {cfg.min_image_side} pixels.")
    return _FORMAT_TO_EXT[fmt], width, height


def store_image(data: bytes, ext: str) -> tuple[str, str]:
    """Write bytes under a generated name. Returns (stored_filename, sha256)."""
    cfg = settings()
    cfg.image_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (cfg.image_dir / name).write_bytes(data)
    return name, hashlib.sha256(data).hexdigest()


def image_path(stored_filename: str) -> Path:
    # stored names are generated hex + extension; reject anything else (path traversal guard)
    if Path(stored_filename).name != stored_filename:
        raise InvalidImageError("Invalid image reference.")
    return settings().image_dir / stored_filename
