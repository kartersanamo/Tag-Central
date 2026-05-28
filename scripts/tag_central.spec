# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Tag Center — onedir bundle for fast startup (no one-file extract)."""

import sys
from pathlib import Path

ROOT = Path(SPEC).resolve().parent.parent

block_cipher = None

# Lazy-import pandas/openpyxl at runtime; list them explicitly without collecting all submodules.
hiddenimports = [
    "pandas",
    "openpyxl",
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
    "pandas.plotting",
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
    name="Tag Center",
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
    name="Tag Center",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Tag Center.app",
        icon=icon_file,
        bundle_identifier="com.eco.tagcentral",
        info_plist={
            "CFBundleName": "Tag Center",
            "CFBundleDisplayName": "Tag Center",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "CFBundleIdentifier": "com.eco.tagcentral",
            "NSHumanReadableCopyright": "Copyright © ECO. All rights reserved.",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.13",
        },
    )
