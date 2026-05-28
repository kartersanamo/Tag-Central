# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Tag Center (shared by macOS and Windows build scripts)."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPEC).resolve().parent.parent

block_cipher = None

hiddenimports = collect_submodules("pandas") + collect_submodules("openpyxl")

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
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Tag Center",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
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
        },
    )
