# PyInstaller spec for the desktop launcher (pyinstaller builder/desktop.spec
# from the repo root; pyinstaller is a build tool, not a requirements.txt dep).
#
# Result: dist/PortfolioCMS/ — PortfolioCMS (executable) + _internal/ (deps,
# cms/templates, cms/static) + project/ (created next to the executable on
# first launch, not inside _internal/). desktop_launcher.py starts Flask and
# opens the default browser; console=True keeps a small log window open
# (Ctrl+C to quit) — no GUI toolkit dependency (webbrowser is stdlib), same
# on every OS.
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
    # never imported by our code; the PIL hook bundles it "just in case" otherwise (~25 MB)
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
