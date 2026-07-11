"""Static site generator. Atomic build: writes to a temp dir then swaps it in."""
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .models import Article, Home, Page, SiteCss, SiteSeo, Tag, db
from .public_render import Linker, paragraphs, public_context, seo_meta

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["paragraphs"] = paragraphs
    return env


def _write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _sitemap_xml(base_url: str, paths: list) -> str:
    urls = "\n".join(f"  <url><loc>{base_url}/{p}</loc></url>" for p in paths)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def build(app) -> Path:
    """Generate the static site. Returns the published site's path."""
    with app.app_context():
        output = Config.OUTPUT_DIR
        tmp = output.parent / (output.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)

        env = _jinja_env()

        home = db.session.get(Home, 1) or Home(titre="", presentation="")
        seo = db.session.get(SiteSeo, 1)
        base_url = seo.base_url if seo else ""
        nav_tags = Tag.query.order_by(Tag.ordre, Tag.nom).all()
        nav_pages = Page.query.order_by(Page.ordre, Page.id).all()

        def ctx(depth):
            return public_context(Linker("build", depth), home, nav_tags, nav_pages, seo)

        # root-relative paths of every page, collected for sitemap.xml (only
        # meaningful once a public base_url is configured, see docs/app.md)
        sitemap_paths = []

        def page_seo(link, path, **kwargs):
            if base_url:
                sitemap_paths.append(path)
            canonical = f"{base_url}/{path}" if base_url else None
            return seo_meta(link, seo, canonical=canonical, base_url=base_url, **kwargs)

        # home (depth 0)
        articles = Article.query.order_by(Article.poids.desc(), Article.titre).all()
        home_ctx = ctx(0)
        home_ctx.update(page_seo(home_ctx["link"], "", title=home.titre or home.site_titre,
                                  description_source=home.presentation))
        _write(
            tmp / "index.html",
            env.get_template("public/home.html").render(**home_ctx, articles=articles),
        )

        # tag pages — tag/<slug>.html (depth 1)
        for tag in nav_tags:
            tag_ctx = ctx(1)
            tag_ctx.update(page_seo(tag_ctx["link"], f"tag/{tag.slug}.html", title=tag.nom,
                                     description_source=tag.presentation))
            _write(
                tmp / "tag" / f"{tag.slug}.html",
                env.get_template("public/tag.html").render(**tag_ctx, tag=tag),
            )

        # article pages — projet/<slug>.html (depth 1)
        for article in articles:
            article_ctx = ctx(1)
            article_ctx.update(page_seo(article_ctx["link"], f"projet/{article.slug}.html", title=article.titre,
                                         description_source=article.texte, image=article.image))
            _write(
                tmp / "projet" / f"{article.slug}.html",
                env.get_template("public/article.html").render(**article_ctx, article=article),
            )

        # free pages — <slug>.html (depth 0)
        for page in nav_pages:
            page_ctx = ctx(0)
            page_ctx.update(page_seo(page_ctx["link"], f"{page.slug}.html", title=page.titre,
                                      description_source=page.texte, image=page.image))
            _write(
                tmp / f"{page.slug}.html",
                env.get_template("public/page.html").render(**page_ctx, page=page),
            )

        # CSS (from SiteCss) + self-hosted fonts
        (tmp / "static").mkdir(parents=True, exist_ok=True)
        css_row = db.session.get(SiteCss, 1)
        (tmp / "static" / "public.css").write_text(css_row.contenu if css_row else "", encoding="utf-8")
        shutil.copytree(STATIC_DIR / "fonts", tmp / "static" / "fonts")

        # media (images + thumbnails)
        media_dst = tmp / "media"
        media_dst.mkdir(parents=True, exist_ok=True)
        if Config.UPLOAD_DIR.exists():
            for f in Config.UPLOAD_DIR.iterdir():
                if f.is_file():
                    shutil.copy2(f, media_dst / f.name)

        # sitemap.xml (needs an absolute base_url) + robots.txt
        if base_url:
            _write(tmp / "sitemap.xml", _sitemap_xml(base_url, sitemap_paths))
            _write(tmp / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n")
        else:
            _write(tmp / "robots.txt", "User-agent: *\nAllow: /\n")

        # atomic swap: old -> .old, tmp -> output, purge .old
        old = output.parent / (output.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        if output.exists():
            output.rename(old)
        tmp.rename(output)
        if old.exists():
            shutil.rmtree(old)

        return output
