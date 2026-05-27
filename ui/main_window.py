"""Main application window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app_config import DEFAULT_TABLE_COLUMNS


class MainWindow:
    """Builds and manages the primary UI widgets."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.search_var = tk.StringVar()
        self.vessel_var = tk.StringVar(value="ALL")
        self.view_conflicts_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="0 tags")
        self.view_conflicts_check: ttk.Checkbutton | None = None

        self.import_button: ttk.Button | None = None
        self.save_button: ttk.Button | None = None
        self.refresh_button: ttk.Button | None = None
        self.reset_filter_button: ttk.Button | None = None
        self.change_tag_button: ttk.Button | None = None
        self.vessel_combo: ttk.Combobox | None = None
        self.tree: ttk.Treeview | None = None
        self.context_menu: tk.Menu | None = None

        self._build_styles()
        self._build_layout()

    def _build_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f5f7fa")
        style.configure("Header.TLabel", font=("Helvetica", 17, "bold"))
        style.configure("Subtitle.TLabel", foreground="#4b5563")

    def _build_layout(self) -> None:
        self.root.configure(bg="#f5f7fa")

        main = ttk.Frame(self.root, style="App.TFrame", padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Tag Central", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            main,
            text="Synchronize, review, and export vessel tag changes.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        control_bar = ttk.Frame(main)
        control_bar.pack(fill="x")

        self.import_button = ttk.Button(control_bar, text="Import Spreadsheet")
        self.save_button = ttk.Button(control_bar, text="Save")
        self.refresh_button = ttk.Button(control_bar, text="Refresh")
        self.change_tag_button = ttk.Button(control_bar, text="Edit Selected Tag")
        self.import_button.pack(side="left", padx=(0, 8))
        self.save_button.pack(side="left", padx=8)
        self.refresh_button.pack(side="left", padx=8)
        self.change_tag_button.pack(side="left", padx=8)

        filter_bar = ttk.Frame(main)
        filter_bar.pack(fill="x", pady=(12, 10))
        ttk.Label(filter_bar, text="Vessel").pack(side="left", padx=(0, 8))
        self.vessel_combo = ttk.Combobox(
            filter_bar, state="readonly", textvariable=self.vessel_var, width=24
        )
        self.vessel_combo.pack(side="left", padx=(0, 8))
        self.reset_filter_button = ttk.Button(filter_bar, text="Reset Filter")
        self.reset_filter_button.pack(side="left", padx=(0, 18))

        ttk.Label(filter_bar, text="Search").pack(side="left", padx=(0, 8))
        ttk.Entry(filter_bar, textvariable=self.search_var, width=40).pack(
            side="left", padx=(0, 8)
        )
        self.view_conflicts_check = ttk.Checkbutton(
            filter_bar,
            text="View Conflicts (0)",
            variable=self.view_conflicts_var,
        )
        self.view_conflicts_check.pack(side="left", padx=(12, 0))

        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame, columns=DEFAULT_TABLE_COLUMNS, show="headings", height=16
        )
        self.tree.heading("tag_name", text="Tag")
        self.tree.heading("description", text="Description")
        self.tree.heading("vessels", text="Vessels")
        self.tree.column("tag_name", width=220, anchor="w")
        self.tree.column("description", width=360, anchor="w")
        self.tree.column("vessels", width=520, anchor="w")
        self.tree.tag_configure("conflict", background="#fff4f4")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edit Tag")

        status = ttk.Label(main, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", pady=(8, 0))

    def set_conflict_count(self, count: int) -> None:
        """Updates the View Conflicts checkbox label with the current count."""
        if self.view_conflicts_check is not None:
            self.view_conflicts_check.configure(text=f"View Conflicts ({count})")
