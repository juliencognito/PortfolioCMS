"""Slug generation from titles, with accent handling."""
import re
import unicodedata


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "sans-titre"


def unique_slug(base: str, exists) -> str:
    """Retourne un slug unique. `exists(slug) -> bool` teste la collision en base."""
    slug = slugify(base)
    candidate = slug
    i = 2
    while exists(candidate):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate
