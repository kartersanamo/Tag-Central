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
    """Writable per-user data directory (database, exports, backups)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    return base / APP_NAME.replace(" ", "")


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
    for folder in (root, root / "exports", root / "backups"):
        folder.mkdir(parents=True, exist_ok=True)

    alias_target = root / "alias_rules.json"
    alias_source = default_alias_rules_path()
    if not alias_target.exists() and alias_source.exists():
        alias_target.write_text(alias_source.read_text(encoding="utf-8"), encoding="utf-8")

    return root
