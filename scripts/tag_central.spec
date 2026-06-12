# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Tag Central — onedir bundle for fast startup (no one-file extract)."""

import sys
from pathlib import Path

ROOT = Path(SPEC).resolve().parent.parent

block_cipher = None

_SKIP_DIRS = {"tests", "scripts", ".venv", "build", "dist", "__pycache__"}


def _project_hiddenimports() -> list[str]:
    """Bundle all app packages; main.py lazy-imports after splash so Analysis misses them."""
    modules: list[str] = []
    for py_file in ROOT.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in py_file.parts):
            continue
        if py_file.name in {"run_tests.py", "generate_icons.py"}:
            continue
        relative = py_file.relative_to(ROOT)
        if relative.name == "__init__.py":
            continue
        modules.append(".".join(relative.with_suffix("").parts))
    return sorted(set(modules))


# Lazy-import pandas/openpyxl at runtime; list them explicitly without collecting all submodules.
hiddenimports = _project_hiddenimports() + [
    "pandas",
    "pandas.plotting",
    "openpyxl",
    "docx",
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.tslibs.np_datetime",
]

excludes = [
    "matplotlib",
    "scipy",
    "pytest",
    "unittest",
    "IPython",
    "jupyter",
    "notebook",
    "sphinx",
    "pandas.tests",
    "tkinter.test",
    "setuptools",
    "distutils",
]

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "alias_rules.json"), "."),
]

if sys.platform == "darwin":
    icon_file = str(ROOT / "assets" / "icon.icns")
elif sys.platform == "win32":
    icon_file = str(ROOT / "assets" / "icon.ico")
else:
    icon_file = str(ROOT / "assets" / "icon-256.png")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Tag Central",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Tag Central",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Tag Central.app",
        icon=icon_file,
        bundle_identifier="com.eco.tagcentral",
        info_plist={
            "CFBundleName": "Tag Central",
            "CFBundleDisplayName": "Tag Central",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "CFBundleIdentifier": "com.eco.tagcentral",
            "NSHumanReadableCopyright": "Copyright © ECO. All rights reserved.",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.13",
        },
    )
