"""Main application window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app_config import CONFLICT_GROUP_COLORS, DEFAULT_TABLE_COLUMNS, PROGRAM_FILTER_VALUES


class MainWindow:
    """Builds and manages the primary UI widgets."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.search_var = tk.StringVar()
        self.vessel_var = tk.StringVar(value="ALL")
        self.program_filter_var = tk.StringVar(value="ALL")
        self.view_conflicts_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="0 tags")
        self.view_conflicts_check: ttk.Checkbutton | None = None
        self.find_text_var = tk.StringVar()
        self.replace_text_var = tk.StringVar()
        self.find_scope_var = tk.StringVar(value="both")
        self.preview_changes_var = tk.BooleanVar(value=True)
        self.find_replace_status_var = tk.StringVar(
            value="Enter find text to filter matching rows"
        )

        self.import_button: ttk.Button | None = None
        self.import_proficy_button: ttk.Button | None = None
        self.import_cimplicity_button: ttk.Button | None = None
        self.align_selected_button: ttk.Button | None = None
        self.cimplicity_review_button: ttk.Button | None = None
        self.cimplicity_tasks_button: ttk.Button | None = None
        self.program_filter_combo: ttk.Combobox | None = None
        self.backups_button: ttk.Button | None = None
        self.refresh_button: ttk.Button | None = None
        self.export_changes_button: ttk.Button | None = None
        self.add_tag_button: ttk.Button | None = None
        self.find_replace_button: ttk.Button | None = None
        self.find_replace_apply_button: ttk.Button | None = None
        self.find_replace_clear_button: ttk.Button | None = None
        self.find_scope_combo: ttk.Combobox | None = None
        self.find_replace_bar: ttk.LabelFrame | None = None
        self._find_replace_visible = True
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
        style.configure("ExportPending.TButton", foreground="#b00020")

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

        self.import_proficy_button = ttk.Button(control_bar, text="Import Proficy…")
        self.import_cimplicity_button = ttk.Button(control_bar, text="Import Cimplicity…")
        self.import_button = self.import_proficy_button
        self.align_selected_button = ttk.Button(
            control_bar, text="Align Selected to Cimplicity"
        )
        self.cimplicity_review_button = ttk.Button(
            control_bar, text="Cimplicity Review (0)"
        )
        self.cimplicity_tasks_button = ttk.Button(
            control_bar, text="Cimplicity Tasks (0)"
        )
        self.backups_button = ttk.Button(control_bar, text="Backups")
        self.refresh_button = ttk.Button(control_bar, text="Refresh")
        self.add_tag_button = ttk.Button(control_bar, text="Add Tag")
        self.find_replace_button = ttk.Button(control_bar, text="Find & Replace ▾")
        self.export_changes_button = ttk.Button(control_bar, text="Export Changes (0)")
        self.change_tag_button = ttk.Button(control_bar, text="Edit Selected Tag")
        self.import_proficy_button.pack(side="left", padx=(0, 6))
        self.import_cimplicity_button.pack(side="left", padx=6)
        self.align_selected_button.pack(side="left", padx=6)
        self.cimplicity_review_button.pack(side="left", padx=6)
        self.cimplicity_tasks_button.pack(side="left", padx=6)
        self.backups_button.pack(side="left", padx=6)
        self.refresh_button.pack(side="left", padx=6)
        self.add_tag_button.pack(side="left", padx=6)
        self.find_replace_button.pack(side="left", padx=6)
        self.export_changes_button.pack(side="left", padx=6)
        self.change_tag_button.pack(side="left", padx=6)

        self.find_replace_bar = ttk.LabelFrame(main, text="Find & Replace", padding=10)
        self.find_replace_bar.pack(fill="x", pady=(10, 8))
        ttk.Label(self.find_replace_bar, text="Find").pack(side="left", padx=(0, 6))
        ttk.Entry(self.find_replace_bar, textvariable=self.find_text_var, width=28).pack(
            side="left", padx=(0, 6)
        )
        ttk.Label(self.find_replace_bar, text="Replace").pack(side="left", padx=(0, 6))
        ttk.Entry(self.find_replace_bar, textvariable=self.replace_text_var, width=28).pack(
            side="left", padx=(0, 6)
        )
        ttk.Label(self.find_replace_bar, text="Scope").pack(side="left", padx=(0, 6))
        self.find_scope_combo = ttk.Combobox(
            self.find_replace_bar,
            textvariable=self.find_scope_var,
            values=("tag", "description", "both"),
            state="readonly",
            width=14,
        )
        self.find_scope_combo.pack(side="left", padx=(0, 6))
        ttk.Checkbutton(
            self.find_replace_bar,
            text="Preview Changes",
            variable=self.preview_changes_var,
        ).pack(side="left", padx=(0, 6))
        self.find_replace_apply_button = ttk.Button(self.find_replace_bar, text="Apply")
        self.find_replace_apply_button.pack(side="left", padx=(0, 8))
        self.find_replace_clear_button = ttk.Button(self.find_replace_bar, text="Clear")
        self.find_replace_clear_button.pack(side="left", padx=(0, 8))
        ttk.Label(self.find_replace_bar, textvariable=self.find_replace_status_var).pack(
            side="right", padx=(6, 0)
        )

        filter_bar = ttk.Frame(main)
        filter_bar.pack(fill="x", pady=(12, 10))  
        ttk.Label(filter_bar, text="Vessel").pack(side="left", padx=(0, 8))
        self.vessel_combo = ttk.Combobox(
            filter_bar, state="readonly", textvariable=self.vessel_var, width=24
        )
        self.vessel_combo.pack(side="left", padx=(0, 8))
        self.reset_filter_button = ttk.Button(filter_bar, text="Reset Filter")
        self.reset_filter_button.pack(side="left", padx=(0, 18))

        ttk.Label(filter_bar, text="Program").pack(side="left", padx=(0, 8))
        self.program_filter_combo = ttk.Combobox(
            filter_bar,
            state="readonly",
            textvariable=self.program_filter_var,
            values=PROGRAM_FILTER_VALUES,
            width=16,
        )
        self.program_filter_combo.pack(side="left", padx=(0, 18))

        ttk.Label(filter_bar, text="Search").pack(side="left", padx=(0, 8))
        ttk.Entry(filter_bar, textvariable=self.search_var, width=40).pack(
            side="left", padx=(0, 8)
        )
        self.view_conflicts_check = ttk.Checkbutton(
            filter_bar,
            text="View Internal Mismatches (0)",
            variable=self.view_conflicts_var,
        )
        self.view_conflicts_check.pack(side="left", padx=(12, 0))

        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame, columns=DEFAULT_TABLE_COLUMNS, show="headings", height=16
        )
        self.tree.heading("row_number", text="#")
        self.tree.heading("tag_name", text="Tag")
        self.tree.heading("proficy_name", text="Proficy Name")
        self.tree.heading("cimplicity_pt_id", text="Cimplicity PT_ID")
        self.tree.heading("description", text="Description")
        self.tree.heading("address", text="Address")
        self.tree.heading("sync_status", text="Sync")
        self.tree.heading("conflict_group", text="Group")
        self.tree.heading("conflicts_with", text="Conflicts With")
        self.tree.heading("vessels", text="Vessels")
        self.tree.column("row_number", width=55, anchor="center")
        self.tree.column("tag_name", width=150, anchor="w")
        self.tree.column("proficy_name", width=140, anchor="w")
        self.tree.column("cimplicity_pt_id", width=140, anchor="w")
        self.tree.column("description", width=200, anchor="w")
        self.tree.column("address", width=110, anchor="w")
        self.tree.column("sync_status", width=100, anchor="w")
        self.tree.column("conflict_group", width=60, anchor="center")
        self.tree.column("conflicts_with", width=160, anchor="w")
        self.tree.column("vessels", width=140, anchor="w")
        for index, color in enumerate(CONFLICT_GROUP_COLORS):
            self.tree.tag_configure(f"conflict_g{index}", background=color)
        self.tree.tag_configure("find_match", background="#fef3c7")
        self.tree.tag_configure("sync_drift", background="#fff3e0")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edit Tag")
        self.context_menu.add_command(label="Align to Cimplicity")
        self.context_menu.add_command(label="Increment descriptions", state="disabled")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Add Tag")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Tag")

        status = ttk.Label(main, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", pady=(8, 0))

    def set_review_queue_count(self, count: int) -> None:
        if self.cimplicity_review_button is not None:
            self.cimplicity_review_button.configure(
                text=f"Cimplicity Review ({count})"
            )

    def set_manual_tasks_count(self, count: int) -> None:
        if self.cimplicity_tasks_button is not None:
            self.cimplicity_tasks_button.configure(
                text=f"Cimplicity Tasks ({count})"
            )

    def set_conflict_count(self, count: int) -> None:
        """Updates the View Internal Mismatches checkbox label with the current count."""
        if self.view_conflicts_check is not None:
            self.view_conflicts_check.configure(
                text=f"View Internal Mismatches ({count})"
            )

    def set_pending_change_count(self, count: int) -> None:
        """Updates export button text/style based on pending changes."""
        if self.export_changes_button is None:
            return
        self.export_changes_button.configure(text=f"Export Changes ({count})")
        if count > 0:
            self.export_changes_button.configure(style="ExportPending.TButton")
        else:
            self.export_changes_button.configure(style="TButton")

    def set_find_replace_status(
        self,
        *,
        find_active: bool,
        match_count: int,
        change_count: int,
        preview_on: bool,
    ) -> None:
        """Updates the find/replace status line."""
        parts: list[str] = []
        if find_active:
            parts.append(f"{match_count} match{'es' if match_count != 1 else ''}")
        if change_count > 0:
            label = "Preview" if preview_on else "Pending"
            parts.append(
                f"{label}: {change_count} change{'s' if change_count != 1 else ''}"
            )
        if not parts:
            self.find_replace_status_var.set("Enter find text to filter matching rows")
            return
        self.find_replace_status_var.set(" · ".join(parts))

    def toggle_find_replace_visibility(self) -> None:
        """Shows/hides the find & replace section and updates button text."""
        if self.find_replace_bar is None or self.find_replace_button is None:
            return
        if self._find_replace_visible:
            self.find_replace_bar.pack_forget()
            self.find_replace_button.configure(text="Find & Replace ▸")
            self._find_replace_visible = False
            return
        self.find_replace_bar.pack(fill="x", pady=(10, 8), before=self.vessel_combo.master)
        self.find_replace_button.configure(text="Find & Replace ▾")
        self._find_replace_visible = True
