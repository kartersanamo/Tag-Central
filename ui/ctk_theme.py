"""CustomTkinter theme setup for Tag Center."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from app_identity import bundle_root, is_frozen

BRAND_TEAL = "#0d6b7a"
BRAND_TEAL_HOVER = "#0a5561"
BRAND_TEAL_LIGHT = "#1a8a9a"
ACCENT_WARNING = "#c62828"
ACCENT_WARNING_HOVER = "#9e1f1f"
SURFACE = "#2b2b2b"
SURFACE_ELEVATED = "#333333"
TEXT_MUTED = "#9ca3af"
CORNER_RADIUS = 8
FONT_FAMILY = "Helvetica Neue"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 13)
FONT_BODY = (FONT_FAMILY, 13)
FONT_SMALL = (FONT_FAMILY, 12)

_theme_applied = False


def _theme_path() -> Path:
    if is_frozen():
        return bundle_root() / "ui" / "tag_central_theme.json"
    return Path(__file__).with_name("tag_central_theme.json")


def apply_ctk_theme() -> None:
    """Applies dark mode and Tag Center brand colors (idempotent)."""
    global _theme_applied
    if _theme_applied:
        return
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme(str(_theme_path()))
    _theme_applied = True


def button_accent_kwargs() -> dict[str, str]:
    """Primary action button colors."""
    return {"fg_color": BRAND_TEAL, "hover_color": BRAND_TEAL_HOVER}


def button_warning_kwargs() -> dict[str, str]:
    """Highlight for pending export / tasks."""
    return {"fg_color": ACCENT_WARNING, "hover_color": ACCENT_WARNING_HOVER}


def button_neutral_kwargs() -> dict[str, str]:
    """Secondary / toolbar button colors."""
    return {"fg_color": "#404040", "hover_color": "#505050"}
