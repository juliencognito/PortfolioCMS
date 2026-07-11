"""Generates -large/-medium/-small variants on upload. No upscaling.

Photos (jpg/jpeg source, and anything else not explicitly kept) are
re-encoded to WebP: smaller than JPEG at equivalent quality, no extra
dependency (Pillow already ships WebP support). PNG/GIF/WebP sources are
kept in their own format (transparency, animation, or already optimal)."""
import uuid
from pathlib import Path

from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

_KEEP_EXTS = {".png", ".webp", ".gif"}


def allowed(filename: str, allowed_ext: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def variant_name(filename: str, size: str) -> str:
    """`abc.jpg`, 'large' -> `abc-large.jpg`."""
    p = Path(filename)
    return f"{p.stem}-{size}{p.suffix}"


def save_image(file_storage, upload_dir: Path, sizes: dict) -> str:
    """Generate the variants and return the logical name <uuid><ext>."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(secure_filename(file_storage.filename or "")).suffix.lower()
    if ext not in _KEEP_EXTS:
        ext = ".webp"  # covers jpg/jpeg and any other unrecognized photo upload
    logical = f"{uuid.uuid4().hex}{ext}"

    try:
        im = Image.open(file_storage.stream)
        im = ImageOps.exif_transpose(im)  # honor EXIF orientation
        if ext == ".webp" and im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        for size_name, width in sizes.items():
            variant = im
            if im.width > width:
                ratio = width / im.width
                variant = im.resize((width, max(1, round(im.height * ratio))), Image.LANCZOS)
            _save_variant(variant, upload_dir / variant_name(logical, size_name), ext)
    except Exception:
        # Fallback if Pillow fails: raw bytes copied into all three variants.
        try:
            file_storage.stream.seek(0)
            raw = file_storage.stream.read()
            for size_name in sizes:
                (upload_dir / variant_name(logical, size_name)).write_bytes(raw)
        except Exception:
            pass
    return logical


def _save_variant(img, dst: Path, ext: str) -> None:
    if ext == ".webp":
        img.save(dst, "WEBP", quality=85, method=6)
    elif ext == ".png":
        img.save(dst, "PNG", optimize=True)
    else:
        img.save(dst)


def delete_image(filename: str, upload_dir: Path,
                 sizes=("large", "medium", "small")) -> None:
    """Delete all variants of an image (no-op if missing)."""
    if not filename:
        return
    for size in sizes:
        try:
            (upload_dir / variant_name(filename, size)).unlink()
        except FileNotFoundError:
            pass
