"""Central CMS configuration. All values are env-overridable (systemd/Docker)."""
import os
import sys
from pathlib import Path

# frozen (PyInstaller): __file__ is in _internal/, not next to the executable.
# Dev mode: this file lives in cms/, so BASE_DIR is its parent (repo root).
# PORTFOLIO_BASE_DIR overrides both: lets a single source checkout develop
# against another site's own project/ + git repo (e.g. one cloned next to
# this one) — project/ AND git_publish's repo_dir move together, unlike
# pointing PORTFOLIO_DB/UPLOADS/OUTPUT there individually, which would leave
# "Publier" pushing into *this* checkout's own git repo instead of the site's.
if os.environ.get("PORTFOLIO_BASE_DIR"):
    BASE_DIR = Path(os.environ["PORTFOLIO_BASE_DIR"]).resolve()
elif getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# per-site data (db, uploads, published site), separate from app code
PROJECT_DIR = BASE_DIR / "project"


class Config:
    # PROD: set PORTFOLIO_SECRET_KEY
    SECRET_KEY = os.environ.get("PORTFOLIO_SECRET_KEY", "dev-change-me-en-prod")

    DB_PATH = Path(os.environ.get("PORTFOLIO_DB", str(PROJECT_DIR / "instance" / "portfolio.sqlite")))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_DIR = Path(os.environ.get("PORTFOLIO_UPLOADS", str(PROJECT_DIR / "uploads")))
    OUTPUT_DIR = Path(os.environ.get("PORTFOLIO_OUTPUT", str(PROJECT_DIR / "output")))

    # whole-request cap; behind nginx also set client_max_body_size
    MAX_CONTENT_LENGTH = int(os.environ.get("PORTFOLIO_MAX_UPLOAD", 64 * 1024 * 1024))

    # max width in px per variant; no upscaling. Sized for actual usage at 2x
    # (retina) pixel density: small = gallery grid thumbs (minmax 220px CSS),
    # medium = card thumbs (minmax 260px CSS), large = cover image + lightbox
    # (up to --maxw 1100px / 92vw).
    IMAGE_SIZES = {
        "large": int(os.environ.get("PORTFOLIO_IMG_LARGE", 1920)),
        "medium": int(os.environ.get("PORTFOLIO_IMG_MEDIUM", 700)),
        "small": int(os.environ.get("PORTFOLIO_IMG_SMALL", 480)),
    }

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
