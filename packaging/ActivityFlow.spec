# PyInstaller spec for ActivityFlow.
#   onedir (default):  pyinstaller packaging/ActivityFlow.spec
#   onefile:           $env:ACTIVITYFLOW_ONEFILE = "1"; pyinstaller packaging/ActivityFlow.spec
# scripts/build.ps1 wraps both. Name, version and copyright come from app/__init__.py.

import os
import sys
from pathlib import Path

from PyInstaller.utils.win32 import versioninfo as vi

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))
import app as meta  # noqa: E402

ONEFILE = os.environ.get("ACTIVITYFLOW_ONEFILE") == "1"
ICON = str(ROOT / "app" / "resources" / "images" / "app.ico")


def version_resource() -> vi.VSVersionInfo:
    numbers = tuple(int(part) for part in meta.APP_VERSION.split(".")[:3])
    numbers += (0,) * (4 - len(numbers))
    strings = {
        "CompanyName": meta.APP_AUTHOR,
        "FileDescription": meta.APP_DESCRIPTION,
        "FileVersion": meta.APP_VERSION,
        "InternalName": meta.APP_NAME,
        "LegalCopyright": meta.APP_COPYRIGHT,
        "OriginalFilename": f"{meta.APP_NAME}.exe",
        "ProductName": meta.APP_NAME,
        "ProductVersion": meta.APP_VERSION,
    }
    return vi.VSVersionInfo(
        ffi=vi.FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            vi.StringFileInfo([vi.StringTable("040904B0", [vi.StringStruct(k, v) for k, v in strings.items()])]),
            vi.VarFileInfo([vi.VarStruct("Translation", [1033, 1200])]),
        ],
    )


# Qt modules the app never uses; excluding them keeps the bundle small.
EXCLUDES = [
    "tkinter", "pytest", "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtLocation", "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets", "PySide6.QtNetworkAuth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2", "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtTextToSpeech", "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets",
    "PySide6.QtWebView", "PySide6.QtHttpServer", "PySide6.QtPdfWidgets",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "app" / "resources"), "app/resources")],
    hiddenimports=["sqlalchemy.dialects.sqlite", "PySide6.QtSvg"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
# Pulled in transitively by Qt plugins but unused by this widgets-only app.
DROP_BINARIES = ("opengl32sw", "qt6quick", "qt6qml", "qt6pdf", "qt6virtualkeyboard", "qtvirtualkeyboard")
a.binaries = [b for b in a.binaries if not any(key in Path(b[0]).name.lower() for key in DROP_BINARIES)]
pyz = PYZ(a.pure)

exe_options = dict(
    name=meta.APP_NAME,
    icon=ICON,
    console=False,
    debug=False,
    strip=False,
    upx=False,
    disable_windowed_traceback=False,
    version=version_resource(),
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **exe_options)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=meta.APP_NAME)
