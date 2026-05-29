"""Application identity, branding paths, and frozen-runtime resource resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Tag Center"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "ECO"
APP_BUNDLE_ID = "com.eco.tagcentral"
APP_COPYRIGHT = f"Copyright © {APP_ORGANIZATION}. All rights reserved."


def is_frozen() -> bool:
    """True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Directory containing packaged read-only resources."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Writable per-user data directory (database, backups, JSON config)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    return base / APP_NAME.replace(" ", "")


def app_install_dir() -> Path:
    """
    Directory where the application lives (for Exports / Documentation siblings).

    macOS .app: folder containing Tag Center.app (e.g. ~/Downloads)
    Windows onedir: folder containing the Tag Center install folder
    Development: project root (folder with main.py), e.g. .../Tag Central/
    """
    if is_frozen():
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            # .../Tag Center.app/Contents/MacOS/Tag Center → .../Downloads
            return executable.parent.parent.parent.parent
        # .../Tag Center/Tag Center.exe → parent of onedir folder
        return executable.parent.parent
    return Path(__file__).resolve().parent


def export_dir(*, project_root: Path | None = None) -> Path:
    """
    Folder for Proficy/Cimplicity export CSVs next to where the app is installed.

    Example: ~/Downloads/Tag Center.app → ~/Downloads/Exports/
    """
    del project_root  # kept for API compatibility with app_config
    return app_install_dir() / "Exports"


def documentation_dir(*, project_root: Path | None = None) -> Path:
    """
    Root folder for generated documentation packages (timestamped subfolders).

    Example: .../Tag Central/Documentation/ or ~/Downloads/Documentation/ (.app in Downloads)
    """
    del project_root
    return app_install_dir() / "Documentation"


def assets_dir() -> Path:
    return bundle_root() / "assets"


def icon_png_path() -> Path:
    return assets_dir() / "icon-256.png"


def icon_ico_path() -> Path:
    return assets_dir() / "icon.ico"


def icon_icns_path() -> Path:
    return assets_dir() / "icon.icns"


def default_alias_rules_path() -> Path:
    return bundle_root() / "alias_rules.json"


def ensure_user_data_layout() -> Path:
    """Creates user data folders and seeds default config from the bundle if missing."""
    root = user_data_dir()
    for folder in (root, root / "backups", export_dir()):
        folder.mkdir(parents=True, exist_ok=True)

    alias_target = root / "alias_rules.json"
    alias_source = default_alias_rules_path()
    if not alias_target.exists() and alias_source.exists():
        alias_target.write_text(alias_source.read_text(encoding="utf-8"), encoding="utf-8")

    return root
