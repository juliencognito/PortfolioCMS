"""Admin interface for the portfolio CMS (Flask). No auth — local use only."""
import os
import threading
from pathlib import Path

import click
from flask import (
    Flask, Response, flash, redirect, render_template, request,
    send_from_directory, url_for,
)

from .build import build
from .config import BASE_DIR, Config
from .fonts import FONTS, preview_css_url
from .git_publish import effective_base_url, git_pull, git_push
from .images import allowed, delete_image, save_image, variant_name
from .models import Article, GalleryImage, GitConfig, Home, Page, SiteCss, SiteSeo, Tag, db
from .public_render import Linker, paragraphs, public_context, seo_meta
from .slugs import unique_slug

STATIC_DIR = Path(__file__).resolve().parent / "static"


def seed_css() -> SiteCss:
    """Create SiteCss(id=1) if missing."""
    css = db.session.get(SiteCss, 1)
    if css is None:
        seed_file = STATIC_DIR / "public.css"
        contenu = seed_file.read_text(encoding="utf-8") if seed_file.exists() else ""
        css = SiteCss(id=1, contenu=contenu)
        db.session.add(css)
        db.session.commit()
    return css


def seed_seo() -> SiteSeo:
    """Create SiteSeo(id=1) if missing."""
    seo = db.session.get(SiteSeo, 1)
    if seo is None:
        seo = SiteSeo(id=1)
        db.session.add(seo)
        db.session.commit()
    return seo


def seed_home() -> Home:
    """Create Home(id=1) if missing."""
    home = db.session.get(Home, 1)
    if home is None:
        home = Home(id=1, site_titre="", titre="", presentation="")
        db.session.add(home)
        db.session.commit()
    return home


def _apply_image_pool(obj, form) -> None:
    """Absent cover_image means "keep current cover"; absent in_gallery
    checkboxes mean "excluded" (unchecked boxes aren't submitted)."""
    valid = {g.filename for g in obj.gallery}
    cover = form.get("cover_image", "")
    if cover in valid:
        obj.image = cover
    in_gallery = set(form.getlist("in_gallery"))
    for g in obj.gallery:
        g.en_texte = g.filename not in in_gallery


def _images_upload_response(obj, owner_field: str) -> dict:
    """Save each uploaded file as a new GalleryImage, return thumbnails
    for image-pool.js to append without reloading the page."""
    start = len(obj.gallery)
    saved = []
    for i, f in enumerate(request.files.getlist("files")):
        if f and f.filename and allowed(f.filename, Config.ALLOWED_EXTENSIONS):
            fn = save_image(f, Config.UPLOAD_DIR, Config.IMAGE_SIZES)
            g = GalleryImage(filename=fn, ordre=start + i, **{owner_field: obj.id})
            db.session.add(g)
            saved.append(g)
    db.session.commit()
    return {"images": [
        {"filename": g.filename, "gid": g.id, "thumb_url": url_for("uploads", filename=variant_name(g.filename, "small"))}
        for g in saved
    ]}


def create_app():
    Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # sqlite needs the dir to exist first

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    app.jinja_env.filters["paragraphs"] = paragraphs
    app.jinja_env.globals["img_variant"] = variant_name

    @app.context_processor
    def _inject_desktop_mode():
        return {"desktop_mode": app.config.get("DESKTOP_MODE", False)}

    # ----------------------------------------------------------- dashboard
    @app.route("/")
    def dashboard():
        return render_template(
            "admin/dashboard.html",
            home=db.session.get(Home, 1),
            articles=Article.query.order_by(Article.poids.desc(), Article.titre).all(),
            tags=Tag.query.order_by(Tag.ordre, Tag.nom).all(),
            pages=Page.query.order_by(Page.ordre, Page.id).all(),
            output_dir=str(Config.OUTPUT_DIR),
        )

    # ---------------------------------------------------------------- home
    @app.route("/accueil/edit", methods=["GET", "POST"])
    def home_edit():
        home = seed_home()
        if request.method == "POST":
            home.titre = request.form.get("titre", "").strip()
            home.presentation = request.form.get("presentation", "")
            home.afficher_projets = bool(request.form.get("afficher_projets"))
            _apply_image_pool(home, request.form)
            db.session.commit()
            flash("Accueil enregistré.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("admin/home_form.html", home=home)

    @app.route("/accueil/images", methods=["POST"])
    def home_images_upload():
        home = db.session.get(Home, 1)
        return _images_upload_response(home, "home_id")

    # ----------------------------------------------------------------- css
    @app.route("/css/edit", methods=["GET", "POST"])
    def css_edit():
        css = seed_css()
        if request.method == "POST":
            css.contenu = request.form.get("contenu", "")
            font_title = request.form.get("font_title", "")
            font_body = request.form.get("font_body", "")
            if font_title in FONTS:
                css.font_title = font_title
            if font_body in FONTS:
                css.font_body = font_body
            db.session.commit()
            flash("CSS enregistré.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("admin/css_form.html", css=css, fonts=sorted(FONTS), preview_css_url=preview_css_url())

    @app.route("/css/preview", methods=["POST"])
    def css_preview():
        """Preview font choices (and the free CSS text) as-is, without saving."""
        css = seed_css()
        css.contenu = request.form.get("contenu", "")
        font_title = request.form.get("font_title", "")
        font_body = request.form.get("font_body", "")
        if font_title in FONTS:
            css.font_title = font_title
        if font_body in FONTS:
            css.font_body = font_body

        articles = Article.query.order_by(Article.poids.desc(), Article.titre).all()
        ctx = _preview_ctx(css=css, articles=articles)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=ctx["home"].titre or ctx["home"].site_titre,
                                 description_source=ctx["home"].presentation))
        html = render_template("public/home.html", **ctx)
        db.session.rollback()  # never persist this preview
        return html

    # ------------------------------------------------------------------ seo
    @app.route("/seo/edit", methods=["GET", "POST"])
    def seo_edit():
        seo = seed_seo()
        home = seed_home()
        if request.method == "POST":
            home.site_titre = request.form.get("site_titre", "").strip()
            seo.base_url = request.form.get("base_url", "").strip().rstrip("/")
            seo.meta_description = request.form.get("meta_description", "").strip()
            seo.twitter_handle = request.form.get("twitter_handle", "").strip()
            seo.robots = request.form.get("robots", "").strip() or "index, follow"
            seo.search_console_verification = request.form.get("search_console_verification", "").strip()

            if request.form.get("remove_og_image") and seo.og_image:
                delete_image(seo.og_image, Config.UPLOAD_DIR)
                seo.og_image = None

            file = request.files.get("og_image")
            if file and file.filename:
                if not allowed(file.filename, Config.ALLOWED_EXTENSIONS):
                    flash("Format d'image non autorisé.", "error")
                    return redirect(request.url)
                if seo.og_image:
                    delete_image(seo.og_image, Config.UPLOAD_DIR)
                seo.og_image = save_image(file, Config.UPLOAD_DIR, Config.IMAGE_SIZES)

            db.session.commit()
            flash("Réglages du site enregistrés.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("admin/seo_form.html", seo=seo, home=home)

    # ------------------------------------------------------------------ git
    @app.route("/git/edit", methods=["GET", "POST"])
    def git_edit():
        cfg = db.session.get(GitConfig, 1)
        if cfg is None:
            cfg = GitConfig(id=1, remote="", token="")
            db.session.add(cfg)
            db.session.commit()
        if request.method == "POST":
            cfg.remote = request.form.get("remote", "").strip()
            cfg.token = request.form.get("token", "").strip()
            db.session.commit()
            flash("Configuration GitLab enregistrée.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("admin/git_form.html", cfg=cfg)

    @app.route("/git/pull", methods=["POST"])
    def git_pull_route():
        cfg = db.session.get(GitConfig, 1)
        try:
            result = git_pull(BASE_DIR, cfg.remote if cfg else "", cfg.token if cfg else "")
        except RuntimeError as exc:
            flash(f"Échec de la récupération depuis GitLab : {exc}", "error")
        else:
            # force reconnect: git_pull() may have swapped the sqlite file
            db.session.remove()
            db.engine.dispose()
            flash(result or "Aucune configuration GitLab renseignée.", "ok")
        return redirect(url_for("dashboard"))

    # ----------------------------------------------------------- articles
    def _slug_exists_article(current_id):
        return lambda s: db.session.query(Article.id).filter(
            Article.slug == s, Article.id != current_id
        ).first() is not None

    @app.route("/articles/new", methods=["GET", "POST"])
    @app.route("/articles/<int:aid>/edit", methods=["GET", "POST"])
    def article_edit(aid=None):
        article = Article.query.get_or_404(aid) if aid else None
        is_new = article is None
        if request.method == "POST":
            titre = request.form.get("titre", "").strip()
            if not titre:
                flash("Le titre est obligatoire.", "error")
                return redirect(request.url)
            if article is None:
                article = Article(titre=titre)
                db.session.add(article)
            article.titre = titre
            with db.session.no_autoflush:
                article.slug = unique_slug(titre, _slug_exists_article(article.id))
            article.poids = int(request.form.get("poids") or 0)
            article.texte = request.form.get("texte", "")
            tag_ids = [int(t) for t in request.form.getlist("tags")]
            article.tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []

            _apply_image_pool(article, request.form)
            # required from the 2nd save on: a brand new article has no id yet to upload into
            if not is_new and not article.image:
                flash("Une image de couverture est obligatoire pour un article.", "error")
                return redirect(request.url)

            db.session.commit()
            flash("Article enregistré.", "ok")
            return redirect(url_for("article_edit", aid=article.id))

        return render_template(
            "admin/article_form.html",
            article=article,
            tags=Tag.query.order_by(Tag.ordre, Tag.nom).all(),
        )

    @app.route("/articles/<int:aid>/delete", methods=["POST"])
    def article_delete(aid):
        article = Article.query.get_or_404(aid)
        if article.image:
            delete_image(article.image, Config.UPLOAD_DIR)
        for g in article.gallery:
            delete_image(g.filename, Config.UPLOAD_DIR)
        db.session.delete(article)
        db.session.commit()
        flash("Article supprimé.", "ok")
        return redirect(url_for("dashboard"))

    @app.route("/gallery/<int:gid>/delete", methods=["POST"])
    def gallery_delete(gid):
        g = GalleryImage.query.get_or_404(gid)
        aid, pid, hid = g.article_id, g.page_id, g.home_id
        owner = g.article or g.page or g.home
        if owner and owner.image == g.filename:
            owner.image = None  # this image was the cover: don't leave a dangling reference
        delete_image(g.filename, Config.UPLOAD_DIR)
        db.session.delete(g)
        db.session.commit()
        if hid:
            return redirect(url_for("home_edit"))
        if pid:
            return redirect(url_for("page_edit", pid=pid))
        return redirect(url_for("article_edit", aid=aid))

    @app.route("/articles/<int:aid>/images", methods=["POST"])
    def article_images_upload(aid):
        article = Article.query.get_or_404(aid)
        return _images_upload_response(article, "article_id")

    @app.route("/articles/preview", methods=["POST"])
    @app.route("/articles/<int:aid>/preview", methods=["POST"])
    def article_preview(aid=None):
        """Preview the form as-is, without saving."""
        article = Article.query.get_or_404(aid) if aid else Article()
        article.titre = request.form.get("titre", "").strip() or "(sans titre)"
        article.texte = request.form.get("texte", "")
        article.poids = int(request.form.get("poids") or 0)
        tag_ids = [int(t) for t in request.form.getlist("tags")]
        article.tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
        _apply_image_pool(article, request.form)
        ctx = _preview_ctx(article=article)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=article.titre,
                                 description_source=article.texte, image=article.image))
        html = render_template("public/article.html", **ctx)
        db.session.rollback()  # never persist this preview
        return html

    # --------------------------------------------------------------- tags
    def _slug_exists_tag(current_id):
        return lambda s: db.session.query(Tag.id).filter(
            Tag.slug == s, Tag.id != current_id
        ).first() is not None

    @app.route("/tags/new", methods=["GET", "POST"])
    @app.route("/tags/<int:tid>/edit", methods=["GET", "POST"])
    def tag_edit(tid=None):
        tag = Tag.query.get_or_404(tid) if tid else None
        if request.method == "POST":
            nom = request.form.get("nom", "").strip()
            if not nom:
                flash("Le nom du tag est obligatoire.", "error")
                return redirect(request.url)
            if tag is None:
                tag = Tag(nom=nom)
                db.session.add(tag)
            tag.nom = nom
            with db.session.no_autoflush:
                tag.slug = unique_slug(nom, _slug_exists_tag(tag.id))
            tag.presentation = request.form.get("presentation", "")
            tag.ordre = int(request.form.get("ordre") or 0)
            db.session.commit()
            flash("Tag enregistré.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("admin/tag_form.html", tag=tag)

    @app.route("/tags/preview", methods=["POST"])
    @app.route("/tags/<int:tid>/preview", methods=["POST"])
    def tag_preview(tid=None):
        """Preview the form as-is, without saving."""
        tag = Tag.query.get_or_404(tid) if tid else Tag()
        tag.nom = request.form.get("nom", "").strip() or "(sans nom)"
        tag.presentation = request.form.get("presentation", "")
        ctx = _preview_ctx(tag=tag)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=tag.nom, description_source=tag.presentation))
        html = render_template("public/tag.html", **ctx)
        db.session.rollback()  # never persist this preview
        return html

    @app.route("/tags/<int:tid>/delete", methods=["POST"])
    def tag_delete(tid):
        tag = Tag.query.get_or_404(tid)
        # article_tags rows are removed automatically; articles themselves are untouched.
        db.session.delete(tag)
        db.session.commit()
        flash("Tag supprimé.", "ok")
        return redirect(url_for("dashboard"))

    # -------------------------------------------------------------- pages
    def _slug_exists_page(current_id):
        return lambda s: db.session.query(Page.id).filter(
            Page.slug == s, Page.id != current_id
        ).first() is not None

    @app.route("/pages/new", methods=["GET", "POST"])
    @app.route("/pages/<int:pid>/edit", methods=["GET", "POST"])
    def page_edit(pid=None):
        page = Page.query.get_or_404(pid) if pid else None
        if request.method == "POST":
            titre = request.form.get("titre", "").strip()
            if not titre:
                flash("Le titre est obligatoire.", "error")
                return redirect(request.url)
            if page is None:
                page = Page(titre=titre)
                db.session.add(page)
            page.titre = titre
            with db.session.no_autoflush:
                page.slug = unique_slug(titre, _slug_exists_page(page.id))
            page.texte = request.form.get("texte", "")
            page.ordre = int(request.form.get("ordre") or 0)
            _apply_image_pool(page, request.form)

            db.session.commit()
            flash("Page enregistrée.", "ok")
            return redirect(url_for("page_edit", pid=page.id))
        return render_template("admin/page_form.html", page=page)

    @app.route("/pages/<int:pid>/images", methods=["POST"])
    def page_images_upload(pid):
        page = Page.query.get_or_404(pid)
        return _images_upload_response(page, "page_id")

    @app.route("/pages/preview", methods=["POST"])
    @app.route("/pages/<int:pid>/preview", methods=["POST"])
    def page_preview(pid=None):
        """Preview the form as-is, without saving."""
        page = Page.query.get_or_404(pid) if pid else Page()
        page.titre = request.form.get("titre", "").strip() or "(sans titre)"
        page.texte = request.form.get("texte", "")
        _apply_image_pool(page, request.form)
        ctx = _preview_ctx(page=page)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=page.titre,
                                 description_source=page.texte, image=page.image))
        html = render_template("public/page.html", **ctx)
        db.session.rollback()  # never persist this preview
        return html

    @app.route("/pages/<int:pid>/delete", methods=["POST"])
    def page_delete(pid):
        page = Page.query.get_or_404(pid)
        if page.image:
            delete_image(page.image, Config.UPLOAD_DIR)
        for g in page.gallery:
            delete_image(g.filename, Config.UPLOAD_DIR)
        db.session.delete(page)
        db.session.commit()
        flash("Page supprimée.", "ok")
        return redirect(url_for("dashboard"))

    # ------------------------------------------------------------ publish
    @app.route("/publish", methods=["POST"])
    def publish():
        out = build(app)
        message = f"Site publié dans {out}."
        cfg = db.session.get(GitConfig, 1)
        try:
            result = git_push(BASE_DIR, cfg.remote if cfg else "", cfg.token if cfg else "")
        except RuntimeError as exc:
            flash(f"{message} Échec de l'envoi vers GitLab : {exc}", "error")
        else:
            pages_url = effective_base_url(db.session.get(SiteSeo, 1), cfg) if result else None
            if pages_url:
                result = f"{result} En ligne : {pages_url}"
            flash(f"{message} {result}" if result else message, "ok")
        return redirect(url_for("dashboard"))

    # ---------------------------------------------------------- desktop only
    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        """Stop the process (desktop package only — no terminal to Ctrl+C when
        launched by double-click, see docs/desktop.md)."""
        if not app.config.get("DESKTOP_MODE"):
            return redirect(url_for("dashboard"))
        threading.Timer(0.3, os._exit, args=(0,)).start()  # let the response flush first
        return "<p>PortfolioCMS est arrêté. Tu peux fermer cette fenêtre.</p>"

    # ------------------------------------------------- serve uploads (preview)
    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(Config.UPLOAD_DIR, filename)

    # ------------------------------------------------------------ preview
    def _preview_ctx(css=None, **extra):
        home = db.session.get(Home, 1) or Home(titre="", presentation="")
        ctx = public_context(
            Linker("preview"),
            home,
            Tag.query.order_by(Tag.ordre, Tag.nom).all(),
            Page.query.order_by(Page.ordre, Page.id).all(),
            db.session.get(SiteSeo, 1),
            css if css is not None else db.session.get(SiteCss, 1),
        )
        ctx.update(extra)
        return ctx

    def _preview_seo(link, seo, **kwargs):
        # canonical=None in preview: only the published site is meant to be indexed
        return seo_meta(link, seo, canonical=None, **kwargs)

    @app.route("/static/public.css")
    def preview_style_css():
        # same path as build, so relative font url()s in the CSS resolve the same
        css = db.session.get(SiteCss, 1)
        return Response(css.contenu if css else "", mimetype="text/css")

    @app.route("/preview/")
    def preview_home():
        articles = Article.query.order_by(Article.poids.desc(), Article.titre).all()
        ctx = _preview_ctx(articles=articles)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=ctx["home"].titre or ctx["home"].site_titre,
                                 description_source=ctx["home"].presentation))
        return render_template("public/home.html", **ctx)

    @app.route("/preview/tag/<slug>")
    def preview_tag(slug):
        tag = Tag.query.filter_by(slug=slug).first_or_404()
        ctx = _preview_ctx(tag=tag)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=tag.nom, description_source=tag.presentation))
        return render_template("public/tag.html", **ctx)

    @app.route("/preview/projets/<slug>")
    def preview_article(slug):
        article = Article.query.filter_by(slug=slug).first_or_404()
        ctx = _preview_ctx(article=article)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=article.titre,
                                 description_source=article.texte, image=article.image))
        return render_template("public/article.html", **ctx)

    @app.route("/preview/page/<slug>")
    def preview_page(slug):
        page = Page.query.filter_by(slug=slug).first_or_404()
        ctx = _preview_ctx(page=page)
        ctx.update(_preview_seo(ctx["link"], ctx["seo"], title=page.titre,
                                 description_source=page.texte, image=page.image))
        return render_template("public/page.html", **ctx)

    # -------------------------------------------------------------- CLI
    @app.cli.command("init-db")
    def init_db():
        """Create tables and seed the home row."""
        db.create_all()
        if db.session.get(Home, 1) is None:
            db.session.add(Home(id=1, site_titre="Mon portfolio", titre="Mon portfolio", presentation=""))
            db.session.commit()
        seed_css()
        seed_seo()
        click.echo("Base initialisée.")

    @app.cli.command("publish")
    def publish_cli():
        """Generate the static site from the CLI."""
        out = build(app)
        click.echo(f"Site publié dans {out}")
        cfg = db.session.get(GitConfig, 1)
        try:
            result = git_push(BASE_DIR, cfg.remote if cfg else "", cfg.token if cfg else "")
        except RuntimeError as exc:
            click.echo(f"Échec de l'envoi vers GitLab : {exc}")
        else:
            if result:
                pages_url = effective_base_url(db.session.get(SiteSeo, 1), cfg)
                click.echo(f"{result} En ligne : {pages_url}" if pages_url else result)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
