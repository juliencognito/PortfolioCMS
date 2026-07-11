"""Curated fonts served via Bunny Fonts (tracking-free Google Fonts mirror)
for the two /css/edit pickers. Each entry checked to carry weights 600/400/
400i on Bunny — see CLAUDE.md."""
import re

_SERIF_FALLBACK = "Georgia, 'Times New Roman', serif"
_SANS_FALLBACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# name -> CSS fallback stack (category-appropriate if the CDN font fails to load)
FONTS = {
    "Fraunces": _SERIF_FALLBACK,
    "Newsreader": _SERIF_FALLBACK,
    "Playfair Display": _SERIF_FALLBACK,
    "Lora": _SERIF_FALLBACK,
    "Cormorant Garamond": _SERIF_FALLBACK,
    "Source Serif 4": _SERIF_FALLBACK,
    "Libre Baskerville": _SERIF_FALLBACK,
    "EB Garamond": _SERIF_FALLBACK,
    "DM Serif Display": _SERIF_FALLBACK,
    "Crimson Text": _SERIF_FALLBACK,
    "Spectral": _SERIF_FALLBACK,
    "Bitter": _SERIF_FALLBACK,
    "Vollkorn": _SERIF_FALLBACK,
    "IBM Plex Serif": _SERIF_FALLBACK,
    "Inter": _SANS_FALLBACK,
    "Work Sans": _SANS_FALLBACK,
    "Manrope": _SANS_FALLBACK,
    "Space Grotesk": _SANS_FALLBACK,
    "Sora": _SANS_FALLBACK,
    "Outfit": _SANS_FALLBACK,
    "Jost": _SANS_FALLBACK,
    "Poppins": _SANS_FALLBACK,
    "DM Sans": _SANS_FALLBACK,
    "Plus Jakarta Sans": _SANS_FALLBACK,
    "Karla": _SANS_FALLBACK,
    "IBM Plex Sans": _SANS_FALLBACK,
}

DEFAULT_FONT_TITLE = "Fraunces"
DEFAULT_FONT_BODY = "Bitter"


def font_stack(name: str) -> str:
    """CSS font-family value: the chosen font plus its fallback stack."""
    fallback = FONTS.get(name, _SERIF_FALLBACK)
    return f'"{name}", {fallback}'


def _bunny_slug(name: str) -> str:
    return name.lower().strip().replace(" ", "-")


def bunny_css_url(font_title: str, font_body: str) -> str:
    """Bunny <link> href: title at 400,600 (600 for headings, 400 as a safety
    net — Bunny loads nothing at all if none of the requested weights exist),
    body at 400,400i. No bold weight: **gras** stays synthetic bold."""
    title_slug = _bunny_slug(font_title)
    body_slug = _bunny_slug(font_body)
    if title_slug == body_slug:
        return f"https://fonts.bunny.net/css?family={title_slug}:400,400i,600"
    return f"https://fonts.bunny.net/css?family={title_slug}:400,600|{body_slug}:400,400i"


def preview_css_url() -> str:
    """One Bunny request loading every curated font, for instant /css/edit preview."""
    slugs = sorted({_bunny_slug(name) for name in FONTS})
    family = "|".join(f"{slug}:400,400i,600" for slug in slugs)
    return f"https://fonts.bunny.net/css?family={family}"


_FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}\s*", re.DOTALL)
_FONT_VAR_RE = re.compile(r"[ \t]*--font-(?:title|body):[^;]*;\n?")
_SELF_HOSTED_COMMENT_RE = re.compile(r"/\*\s*self-hosted fonts[^*]*\*/\n?", re.IGNORECASE)


def strip_legacy_font_css(css_text: str) -> str:
    """One-off migration: strip self-hosted @font-face/--font-* leftovers
    from a CSS blob seeded before the Bunny CDN switch — see CLAUDE.md."""
    text = _SELF_HOSTED_COMMENT_RE.sub("", css_text)
    text = _FONT_FACE_RE.sub("", text)
    text = _FONT_VAR_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).lstrip("\n")
