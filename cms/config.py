"""Central CMS configuration. All values are env-overridable (systemd/Docker)."""
import os
import sys
from pathlib import Path

# PORTFOLIO_BASE_DIR: develop against another site's project/+git repo
# (moves BASE_DIR and PROJECT_DIR together, so "Publier" targets that repo).
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

    # set by desktop_launcher.py: shows the "Quitter" button (see docs/desktop.md)
    DESKTOP_MODE = os.environ.get("PORTFOLIO_DESKTOP") == "1"

    DB_PATH = Path(os.environ.get("PORTFOLIO_DB", str(PROJECT_DIR / "instance" / "portfolio.sqlite")))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_DIR = Path(os.environ.get("PORTFOLIO_UPLOADS", str(PROJECT_DIR / "uploads")))
    OUTPUT_DIR = Path(os.environ.get("PORTFOLIO_OUTPUT", str(PROJECT_DIR / "output")))

    # whole-request cap; behind nginx also set client_max_body_size
    MAX_CONTENT_LENGTH = int(os.environ.get("PORTFOLIO_MAX_UPLOAD", 64 * 1024 * 1024))

    # max width in px per variant, sized for 2x/retina display; no upscaling
    IMAGE_SIZES = {
        "large": int(os.environ.get("PORTFOLIO_IMG_LARGE", 1920)),
        "medium": int(os.environ.get("PORTFOLIO_IMG_MEDIUM", 700)),
        "small": int(os.environ.get("PORTFOLIO_IMG_SMALL", 480)),
    }

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
