# PyInstaller spec for POLTRACKER.app. Build with scripts/build-macos.sh (run from the repository root).
# Reproducible: everything comes from the repository and the pinned virtualenv; no network at build time.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent.parent  # noqa: F821 - SPECPATH is provided by PyInstaller
VERSION = "0.1.0"  # keep in sync with poltracker.desktop.APP_VERSION (a test checks this)
BUNDLE_ID = "com.roamingwizards.poltracker"

frontend = ROOT / "frontend" / "dist"
if not (frontend / "index.html").is_file():
    raise SystemExit("frontend/dist is missing: run scripts/build-macos.sh (it builds the frontend first).")

datas = [
    (str(frontend), "frontend_dist"),
    (str(ROOT / "migrations"), "migrations"),  # Alembic env, template and versions, run in-process at startup
]
datas += collect_data_files("yfinance")
datas += collect_data_files("curl_cffi")
datas += collect_data_files("certifi")

hiddenimports = (
    collect_submodules("poltracker")
    + collect_submodules("uvicorn")
    + collect_submodules("alembic.ddl")
    + collect_submodules("sqlalchemy.dialects.sqlite")
    + collect_submodules("yfinance")
    + collect_submodules("curl_cffi")
    + ["sqlite3", "webview.platforms.cocoa"]
)

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "macos" / "launcher.py")],
    pathex=[str(ROOT / "backend")],
    datas=datas,
    hiddenimports=hiddenimports,
    # PostgreSQL support stays in the repository for future web deployment but is not needed offline on a Mac.
    excludes=["psycopg", "psycopg_binary", "psycopg_pool", "pytest", "tkinter", "matplotlib", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="POLTRACKER",
    console=False,  # windowed app: no Terminal
    target_arch="arm64",
    strip=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="POLTRACKER")  # noqa: F821

_icon = ROOT / "packaging" / "macos" / "icon" / "POLTRACKER.icns"
app = BUNDLE(  # noqa: F821
    coll,
    name="POLTRACKER.app",
    icon=str(_icon) if _icon.is_file() else None,  # placeholder until an icon is supplied
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleName": "POLTRACKER",
        "CFBundleDisplayName": "POLTRACKER",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.finance",
        "NSHumanReadableCopyright": "POLTRACKER",
    },
)
