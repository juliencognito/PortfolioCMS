"""Data model for the portfolio CMS. No user accounts (see CLAUDE.md)."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Home(db.Model):
    """Singleton (id=1). site_titre: site name, every page. titre: home <h1> only."""
    id = db.Column(db.Integer, primary_key=True)
    site_titre = db.Column(db.String(200), nullable=False, default="")
    titre = db.Column(db.String(200), nullable=False, default="")
    presentation = db.Column(db.Text, nullable=False, default="")


class SiteCss(db.Model):
    """Public site CSS, editable from the admin. Singleton (id=1)."""
    id = db.Column(db.Integer, primary_key=True)
    contenu = db.Column(db.Text, nullable=False, default="")


class SiteSeo(db.Model):
    """Global SEO settings, singleton (id=1). No per-article overrides: each
    page's own title/text/image already feed description/og:*, this only
    holds site-wide fallbacks and metadata."""
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String(255), nullable=False, default="")  # e.g. https://user.gitlab.io/site (no trailing slash) — enables sitemap.xml + canonical/OG absolute URLs
    meta_description = db.Column(db.Text, nullable=False, default="")  # fallback when a page has no derivable summary
    og_image = db.Column(db.String(255), nullable=True)  # fallback social image (logical filename), e.g. for Home/tags
    twitter_handle = db.Column(db.String(120), nullable=False, default="")  # e.g. @handle, for twitter:site
    robots = db.Column(db.String(120), nullable=False, default="index, follow")
    search_console_verification = db.Column(db.String(255), nullable=False, default="")


article_tags = db.Table(
    "article_tags",
    db.Column("article_id", db.Integer, db.ForeignKey("article.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    presentation = db.Column(db.Text, nullable=False, default="")
    ordre = db.Column(db.Integer, nullable=False, default=0)  # nav order

    articles = db.relationship(
        "Article",
        secondary=article_tags,
        back_populates="tags",
        order_by="Article.poids.desc()",
    )


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    image = db.Column(db.String(255), nullable=True)  # main image (filename)
    poids = db.Column(db.Integer, nullable=False, default=0)  # descending sort weight
    texte = db.Column(db.Text, nullable=False, default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)

    tags = db.relationship(
        "Tag",
        secondary=article_tags,
        back_populates="articles",
        order_by="Tag.ordre, Tag.nom",
    )
    gallery = db.relationship(
        "GalleryImage",
        back_populates="article",
        order_by="GalleryImage.ordre",
        cascade="all, delete-orphan",
    )


class GalleryImage(db.Model):
    """Belongs to an Article OR a Page (exactly one FK set). en_texte: inserted
    via [[image:...]] in the text, hidden from the gallery grid."""
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=True)
    page_id = db.Column(db.Integer, db.ForeignKey("page.id"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    ordre = db.Column(db.Integer, nullable=False, default=0)
    en_texte = db.Column(db.Boolean, nullable=False, default=False)

    article = db.relationship("Article", back_populates="gallery")
    page = db.relationship("Page", back_populates="gallery")


class GitConfig(db.Model):
    """Auto-push config, singleton (id=1). Empty remote/token disables push."""
    id = db.Column(db.Integer, primary_key=True)
    remote = db.Column(db.String(255), nullable=False, default="")
    token = db.Column(db.String(255), nullable=False, default="")  # scope: write_repository


class Page(db.Model):
    """Free-standing page (e.g. "about")."""
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    texte = db.Column(db.Text, nullable=False, default="")
    ordre = db.Column(db.Integer, nullable=False, default=0)  # nav order

    gallery = db.relationship(
        "GalleryImage",
        back_populates="page",
        order_by="GalleryImage.ordre",
        cascade="all, delete-orphan",
    )
