"""Dark-styled ttk.Treeview embedded in CustomTkinter frames."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from app_config import CONFLICT_GROUP_COLORS, DEFAULT_TABLE_COLUMNS
from ui.ctk_theme import BRAND_TEAL, SURFACE, SURFACE_ELEVATED

_tree_style_initialized = False

# Dark-mode adjusted row highlight colors
_DARK_CONFLICT_COLORS = (
    "#4a3030",
    "#4a3d28",
    "#4a4528",
    "#2a4030",
    "#283848",
    "#382840",
    "#402838",
    "#284040",
)
_FIND_MATCH_DARK = "#4a4228"
_SYNC_DRIFT_DARK = "#4a3828"


def _init_tree_style(root: ctk.CTk) -> ttk.Style:
    global _tree_style_initialized
    style = ttk.Style(root)
    if not _tree_style_initialized:
        style.theme_use("clam")
        style.configure(
            "TagCentral.Treeview",
            background=SURFACE_ELEVATED,
            foreground="#e5e7eb",
            fieldbackground=SURFACE_ELEVATED,
            borderwidth=0,
            rowheight=26,
            font=("Helvetica Neue", 12),
        )
        style.configure(
            "TagCentral.Treeview.Heading",
            background=BRAND_TEAL,
            foreground="#ffffff",
            relief="flat",
            font=("Helvetica Neue", 12, "bold"),
        )
        style.map(
            "TagCentral.Treeview",
            background=[("selected", BRAND_TEAL)],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "TagCentral.Vertical.TScrollbar",
            background="#404040",
            troughcolor=SURFACE,
            borderwidth=0,
            arrowcolor="#e5e7eb",
        )
        _tree_style_initialized = True
    return style


def create_tag_treeview(
    parent: ctk.CTkFrame,
    *,
    height: int = 16,
) -> tuple[ttk.Treeview, ttk.Scrollbar]:
    """Creates a styled tag table Treeview inside a CTk host frame."""
    root = parent.winfo_toplevel()
    _init_tree_style(root)  # type: ignore[arg-type]

    host = ctk.CTkFrame(parent, fg_color="transparent")
    host.pack(fill="both", expand=True)

    tree = ttk.Treeview(
        host,
        columns=DEFAULT_TABLE_COLUMNS,
        show="headings",
        height=height,
        style="TagCentral.Treeview",
    )
    tree.heading("row_number", text="#")
    tree.heading("tag_name", text="Tag")
    tree.heading("proficy_name", text="Proficy Name")
    tree.heading("cimplicity_pt_id", text="Cimplicity PT_ID")
    tree.heading("description", text="Description")
    tree.heading("address", text="Address")
    tree.heading("sync_status", text="Sync")
    tree.heading("conflict_group", text="Group")
    tree.heading("vessels", text="Vessels")
    tree.column("row_number", width=55, anchor="center")
    tree.column("tag_name", width=150, anchor="w")
    tree.column("proficy_name", width=140, anchor="w")
    tree.column("cimplicity_pt_id", width=140, anchor="w")
    tree.column("description", width=200, anchor="w")
    tree.column("address", width=110, anchor="w")
    tree.column("sync_status", width=100, anchor="w")
    tree.column("conflict_group", width=60, anchor="center")
    tree.column("vessels", width=140, anchor="w")

    for index, _color in enumerate(CONFLICT_GROUP_COLORS):
        dark = _DARK_CONFLICT_COLORS[index % len(_DARK_CONFLICT_COLORS)]
        tree.tag_configure(f"conflict_g{index}", background=dark)
    tree.tag_configure("find_match", background=_FIND_MATCH_DARK)
    tree.tag_configure("sync_drift", background=_SYNC_DRIFT_DARK)

    y_scroll = ttk.Scrollbar(
        host,
        orient="vertical",
        command=tree.yview,
        style="TagCentral.Vertical.TScrollbar",
    )
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    y_scroll.pack(side="right", fill="y")
    return tree, y_scroll


def create_data_treeview(
    parent: ctk.CTkFrame,
    columns: tuple[str, ...],
    headings: dict[str, str],
    column_widths: dict[str, int],
    *,
    height: int = 12,
) -> tuple[ttk.Treeview, ttk.Scrollbar]:
    """Generic dark Treeview for dialog tables."""
    root = parent.winfo_toplevel()
    _init_tree_style(root)  # type: ignore[arg-type]

    host = ctk.CTkFrame(parent, fg_color="transparent")
    host.pack(fill="both", expand=True)

    tree = ttk.Treeview(
        host,
        columns=columns,
        show="headings",
        height=height,
        style="TagCentral.Treeview",
    )
    for column in columns:
        tree.heading(column, text=headings.get(column, column))
        tree.column(column, width=column_widths.get(column, 120), anchor="w")

    y_scroll = ttk.Scrollbar(
        host,
        orient="vertical",
        command=tree.yview,
        style="TagCentral.Vertical.TScrollbar",
    )
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    y_scroll.pack(side="right", fill="y")
    return tree, y_scroll
