"""Desktop launcher for the portfolio CMS, frozen by PyInstaller (see desktop.spec)."""
import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

import webview

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # this file lives in builder/, so BASE_DIR is its parent (repo root)
    BASE_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE_DIR))  # so `cms` is importable from source

PROJECT_DIR = BASE_DIR / "project"
INSTANCE_DIR = PROJECT_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
(PROJECT_DIR / "uploads").mkdir(parents=True, exist_ok=True)

SECRET_KEY_FILE = INSTANCE_DIR / "secret_key"
if SECRET_KEY_FILE.exists():
    secret_key = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
else:
    secret_key = secrets.token_urlsafe(48)
    SECRET_KEY_FILE.write_text(secret_key, encoding="utf-8")

# must be set before importing app (read by config.py on import)
os.environ["PORTFOLIO_SECRET_KEY"] = secret_key
os.environ["PORTFOLIO_DB"] = str(INSTANCE_DIR / "portfolio.sqlite")
os.environ["PORTFOLIO_UPLOADS"] = str(PROJECT_DIR / "uploads")
os.environ["PORTFOLIO_OUTPUT"] = str(PROJECT_DIR / "output")

from cms.app import app as flask_app, seed_css, seed_seo  # noqa: E402
from cms.models import Home, db  # noqa: E402


def _init_db():
    db.create_all()
    if db.session.get(Home, 1) is None:
        db.session.add(Home(id=1, site_titre="Mon portfolio", titre="Mon portfolio", presentation=""))
        db.session.commit()
    seed_css()
    seed_seo()


def _wait_for_server(host, port, timeout=5.0):
    """Wait for the Flask thread to accept connections before opening the window."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)


def main():
    with flask_app.app_context():
        _init_db()

    threading.Thread(
        target=flask_app.run,
        kwargs={"host": "127.0.0.1", "port": 5000, "debug": False, "use_reloader": False},
        daemon=True,
    ).start()
    _wait_for_server("127.0.0.1", 5000)

    webview.create_window("Portfolio CMS", "http://127.0.0.1:5000")
    webview.start()


if __name__ == "__main__":
    main()
