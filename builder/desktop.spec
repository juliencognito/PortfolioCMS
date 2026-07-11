# PyInstaller spec for the desktop launcher.
#
# PyInstaller is a build tool, not a runtime dependency: install it separately
# in the venv (`pip install pyinstaller`), don't add it to requirements.txt.
#
# Build:   pyinstaller builder/desktop.spec   (from the repo root)
# Result:  dist/PortfolioCMS/ (the folder to zip and share):
#            - PortfolioCMS   (executable to launch)
#            - _internal/     (Python + deps + cms/templates, cms/static
#                              bundled in — don't touch)
#            - project/ (instance/, uploads/, output/) created next to the
#              executable on first launch, NOT inside _internal/
#          Launch: double-click from the file manager — desktop_launcher.py
#          opens a native window (pywebview), no terminal or external
#          browser needed (see console=False below). Requires GTK3 + WebKit2
#          on the machine running the binary (present by default on most
#          desktop Linux; the build venv must be created with
#          `python3 -m venv --system-site-packages .venv` so PyInstaller can
#          bundle the gi/PyGObject bindings).
import os

ROOT = os.path.dirname(SPECPATH)  # repo root (SPECPATH = builder/)

block_cipher = None

a = Analysis(
    [os.path.join(SPECPATH, "desktop_launcher.py")],
    pathex=[ROOT],
    binaries=[],
    # destination nested under cms/ to match cms.app's frozen root_path
    # (Flask resolves templates/static relative to the app module's own
    # location, and that module now lives in the cms package)
    datas=[
        (os.path.join(ROOT, "cms", "templates"), os.path.join("cms", "templates")),
        (os.path.join(ROOT, "cms", "static"), os.path.join("cms", "static")),
    ],
    hiddenimports=[],
    hookspath=[],
    # Without this, PyInstaller's GTK hook bundles the ENTIRE system icon
    # theme + all translations (~330 MB), even though the pywebview window
    # only shows Flask content, no GTK widgets with icons.
    hooksconfig={"gi": {"icons": [], "themes": [], "languages": []}},
    runtime_hooks=[],
    # numpy: never imported by our code, but present at the system level (via
    # --system-site-packages, needed for GTK) — without this exclusion, the
    # PIL hook bundles it "just in case" along with its BLAS/LAPACK/gfortran
    # entourage (~25 MB) for numpy interop that's never used here.
    excludes=["numpy"],
    cipher=block_cipher,
)

# PyInstaller's GdkPixbuf hook unconditionally bundles ALL image-decoding
# plugins (AVIF/HEIF/JPEG-XL included, ~25 MB of codecs), even though GTK is
# only used here for the window itself: web content is rendered by WebKit
# (loaded from the system, never bundled), not GdkPixbuf. No hooksconfig
# option for this, so filter manually.
a.binaries = [b for b in a.binaries if "gdk-pixbuf" not in b[0]]
a.datas = [d for d in a.datas if "gdk-pixbuf" not in d[0]]

# Once the plugins above are removed, these codec libraries (AVIF/HEIF/SVG/
# JPEG-XL and their AV1 dependencies) become orphaned — nothing left in the
# package references them (verified via `readelf -d`).
_ORPHANED_CODECS = (
    "libavif", "libheif", "librsvg", "libjxl",
    "libaom", "libsvtav1enc", "librav1e", "libdav1d", "libgav1", "libyuv",
)
a.binaries = [b for b in a.binaries if not b[0].lower().startswith(_ORPHANED_CODECS)]

# The gi hook also bundles the CI runner's own GLib/GObject/GTK/WebKit stack.
# That's actively harmful, not just wasted space: at runtime the bundled
# (older) libglib-2.0 gets loaded into the process first, then a system
# library dlopen'd later by GObject introspection (libwebkit2gtk, libsecret,
# ...) — compiled against the *target machine's own* (newer) glib — fails to
# resolve a symbol against the bundled one still resident in memory
# (observed: "undefined symbol: g_variant_builder_init_static" on a Debian
# 13 host, package built on an older CI runner). GTK3 + WebKit2GTK are
# already a required system dependency on the target machine (see
# docs/desktop.md), so drop the bundled copies entirely and let the dynamic
# linker fall through to the system's own, version-matched libraries.
_SYSTEM_GTK_STACK = (
    "libglib-2.0", "libgobject-2.0", "libgio-2.0", "libgmodule-2.0",
    "libgthread-2.0", "libgtk-3", "libgdk-3", "libgdk_pixbuf-2.0",
    "libpango", "libcairo", "libatk", "libharfbuzz",
    "libwebkit2gtk", "libjavascriptcoregtk", "libsecret",
)
a.binaries = [b for b in a.binaries if not os.path.basename(b[0]).lower().startswith(_SYSTEM_GTK_STACK)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PortfolioCMS",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="PortfolioCMS",
)
