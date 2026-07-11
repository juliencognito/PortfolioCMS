"""Shared between preview and static build: same templates, URL building differs (Linker)."""
import re

from markupsafe import Markup, escape

from .fonts import DEFAULT_FONT_BODY, DEFAULT_FONT_TITLE, bunny_css_url, font_stack
from .images import variant_name

# minimal markup (not full Markdown): **bold**, *italic*, ++underline++,
# `code`, [texte](url), ### / #### / ##### (h3-h5), --- (hr)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_UNDERLINE_RE = re.compile(r"\+\+(.+?)\+\+")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_CODE_RE = re.compile(r"`(.+?)`")
_LINK_RE = re.compile(r"\[(.+?)\]\((.+?)\)")
_HEADING_RE = re.compile(r"^(#{3,5})\s+(.*)$", re.DOTALL)
_HR_RE = re.compile(r"^-{3,}$")
_IMAGE_RE = re.compile(r"^\[\[image:(.+?)\]\]$")


class Linker:
    """URL builder. preview: served by the admin app. build: relative URLs (so
    the site opens via file://); `depth` = dirs between output/ and the page."""

    def __init__(self, mode: str, depth: int = 0):
        assert mode in ("preview", "build")
        self.mode = mode
        self.depth = depth
        self._up = "../" * depth

    def home(self) -> str:
        return "/preview/" if self.mode == "preview" else self._up + "index.html"

    def tag(self, tag) -> str:
        if self.mode == "preview":
            return f"/preview/tag/{tag.slug}"
        return self._up + f"tag/{tag.slug}.html"

    def article(self, article) -> str:
        if self.mode == "preview":
            return f"/preview/projets/{article.slug}"
        return self._up + f"projets/{article.slug}.html"

    def page(self, page) -> str:
        if self.mode == "preview":
            return f"/preview/page/{page.slug}"
        return self._up + f"{page.slug}.html"

    def media(self, filename: str, size: str = "large") -> str:
        if not filename:
            return ""
        if self.mode == "preview":
            return f"/uploads/{variant_name(filename, size)}"
        return self._up + f"media/{variant_name(filename, size)}"

    def css(self) -> str:
        return "/static/public.css" if self.mode == "preview" else self._up + "static/public.css"

    def og_image(self, filename: str, base_url: str = "", size: str = "large") -> str:
        """URL for og:image. Preview: relative (fine for browser preview, no
        crawler involved). Build: absolute via `base_url` (required by OG/
        Twitter crawlers) — empty if `base_url` isn't configured."""
        if not filename:
            return ""
        if self.mode == "preview":
            return self.media(filename, size)
        if not base_url:
            return ""
        return f"{base_url.rstrip('/')}/media/{variant_name(filename, size)}"


def _inline_markup(line: str) -> str:
    """Apply link/bold/italic/underline/code to an already-escaped line.
    Link runs first so `**bold**` inside link text still gets processed."""
    line = _LINK_RE.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', line)
    line = _CODE_RE.sub(r"<code>\1</code>", line)
    line = _BOLD_RE.sub(r"<strong>\1</strong>", line)
    line = _UNDERLINE_RE.sub(r"<u>\1</u>", line)
    line = _ITALIC_RE.sub(r"<em>\1</em>", line)
    return line


def _render_block(block: str, link: "Linker") -> str:
    image = _IMAGE_RE.match(block)
    if image:
        name = escape(image.group(1).strip())
        return f'<figure class="prose-image"><img src="{link.media(name, size="large")}" loading="lazy"></figure>'
    heading = _HEADING_RE.match(block)
    if heading:
        level = len(heading.group(1))
        content = _inline_markup(escape(heading.group(2).strip()))
        return f"<h{level}>{content}</h{level}>"
    if _HR_RE.match(block):
        return "<hr>"
    lines = "<br>".join(_inline_markup(escape(line)) for line in block.split("\n"))
    return f"<p>{lines}</p>"


def paragraphs(text: str, link: "Linker") -> Markup:
    """Plain text to HTML paragraphs (blank line = <p>, single = <br>);
    also handles the [[image:...]] block marker (needs `link` for its URL)."""
    if not text:
        return Markup("")
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    return Markup("".join(_render_block(b, link) for b in blocks))


def public_context(link: Linker, home, nav_tags, nav_pages, seo=None, css=None) -> dict:
    """Common context injected into every public template."""
    font_title = (css.font_title if css else None) or DEFAULT_FONT_TITLE
    font_body = (css.font_body if css else None) or DEFAULT_FONT_BODY
    return {
        "link": link,
        "home": home,
        "nav_tags": nav_tags,
        "nav_pages": nav_pages,
        "seo": seo,
        "fonts_css_url": bunny_css_url(font_title, font_body),
        "font_title_stack": font_stack(font_title),
        "font_body_stack": font_stack(font_body),
    }


def plain_summary(text: str, max_len: int = 160) -> str:
    """First paragraph of `text`, markup markers stripped, truncated — for use
    as a meta description (no per-article field: derived from existing content)."""
    if not text:
        return ""
    first_block = text.replace("\r\n", "\n").split("\n\n", 1)[0].strip()
    if _IMAGE_RE.match(first_block) or _HR_RE.match(first_block) or _HEADING_RE.match(first_block):
        return ""
    plain = _LINK_RE.sub(r"\1", first_block)
    plain = _CODE_RE.sub(r"\1", plain)
    plain = _BOLD_RE.sub(r"\1", plain)
    plain = _UNDERLINE_RE.sub(r"\1", plain)
    plain = _ITALIC_RE.sub(r"\1", plain)
    plain = " ".join(plain.split())
    if len(plain) > max_len:
        plain = plain[:max_len].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return plain


def seo_meta(link: "Linker", seo, *, title: str, description_source: str = "",
             image: str = None, canonical: str = None, base_url: str = "") -> dict:
    """Per-page meta context for templates/public/base.html: title, description
    and image use the page's own content first, falling back to the global
    `SiteSeo` settings only when a page has nothing of its own (see docs/app.md
    — no per-article SEO fields, by design)."""
    image = image or (seo.og_image if seo else None)
    return {
        "meta_title": title,
        "meta_description": plain_summary(description_source) or (seo.meta_description if seo else ""),
        "meta_image_url": link.og_image(image, base_url) if image else "",
        "robots": (seo.robots if seo else "") or "index, follow",
        "canonical": canonical,
    }
