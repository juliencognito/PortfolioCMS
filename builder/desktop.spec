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
import sys

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

# The gi hook doesn't just bundle GTK: it drags in the CI runner's entire
# native dependency closure (GLib/GObject/GTK/WebKit, but also transitive
# base-OS libs like libmount/libblkid/libselinux/libpcre2...). Bundling any
# of it is actively harmful, not just wasted space: at runtime the bundled
# (CI runner's) copy loads first, then some other system library dlopen'd
# later by GObject introspection — compiled against the *target machine's
# own* version of that same dependency — fails to resolve a symbol against
# the stale one already resident in memory. Piège vécu, in two steps: first
# libglib itself (`undefined symbol: g_variant_builder_init_static`, fixed by
# excluding the GTK stack by name), then libmount transitively pulled in by
# libgio (`version 'MOUNT_2_40' not found`) — a whack-a-mole that never ends
# by naming libraries one at a time. GTK3 + WebKit2 + PyGObject are already a
# required system dependency on the target machine (see docs/desktop.md), so
# instead drop every shared library PyInstaller sourced from a system
# directory, keeping only what's genuinely vendored by a wheel in this venv
# (e.g. Pillow's own libjpeg/libwebp, which must stay bundled since the
# target system doesn't provide them) plus the interpreter itself. Python
# extension modules (gi's own _gi.so included) are a different TOC type and
# always kept regardless of where they live.
_VENV_PREFIX = os.path.normpath(sys.prefix)


def _keep_binary(entry):
    dest, source, typecode = entry
    if typecode != "BINARY":
        return True  # EXTENSION (Python modules, e.g. gi/_gi.so): always needed
    if os.path.basename(dest).lower().startswith("libpython"):
        return True  # the interpreter itself
    return os.path.normpath(source).startswith(_VENV_PREFIX)  # wheel-vendored, not system-provided


a.binaries = [b for b in a.binaries if _keep_binary(b)]

# GdkPixbuf's icon themes/translations/image-format loaders are `datas`, a
# separate TOC untouched by the binaries filter above — GTK is only used
# here for the window chrome, web content is rendered by WebKit, not
# GdkPixbuf, so none of this is needed either (~330 MB before this filter).
a.datas = [d for d in a.datas if "gdk-pixbuf" not in d[0]]

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
