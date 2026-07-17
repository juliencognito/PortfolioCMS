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
#          starts the Flask server and opens it in the default browser (see
#          console=True below: a small console window stays open, showing
#          the server log — close it or Ctrl+C to quit). No GUI toolkit
#          dependency (no GTK/WebKit, no pythonnet, no pyobjc): just the
#          stdlib `webbrowser` module, so this is the same on every OS.
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
    hooksconfig={},
    runtime_hooks=[],
    # numpy: never imported by our code, but present in some environments —
    # without this exclusion, the PIL hook bundles it "just in case" along
    # with its BLAS/LAPACK/gfortran entourage (~25 MB) for numpy interop
    # that's never used here.
    excludes=["numpy"],
    cipher=block_cipher,
)

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
    console=True,
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
