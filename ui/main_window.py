"""Main application window."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from app_config import PROGRAM_FILTER_VALUES
from ui.ctk_theme import (
    CORNER_RADIUS,
    FONT_BODY,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    TEXT_MUTED,
    button_accent_kwargs,
    button_neutral_kwargs,
    button_warning_kwargs,
)
from ui.ctk_tree import create_tag_treeview


class MainWindow:
    """Builds and manages the primary UI widgets."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.search_var = tk.StringVar()
        self.vessel_var = tk.StringVar(value="ALL")
        self.program_filter_var = tk.StringVar(value="ALL")
        self.view_conflicts_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="0 tags")
        self.view_conflicts_check: ctk.CTkCheckBox | None = None
        self.array_expand_toggle_button: ctk.CTkButton | None = None
        self.find_text_var = tk.StringVar()
        self.replace_text_var = tk.StringVar()
        self.find_scope_var = tk.StringVar(value="both")
        self.preview_changes_var = tk.BooleanVar(value=True)
        self.find_replace_status_var = tk.StringVar(
            value="Enter find text to filter matching rows"
        )

        self.import_button: ctk.CTkButton | None = None
        self.import_proficy_button: ctk.CTkButton | None = None
        self.import_cimplicity_button: ctk.CTkButton | None = None
        self.cimplicity_review_button: ctk.CTkButton | None = None
        self.cimplicity_tasks_button: ctk.CTkButton | None = None
        self.program_filter_combo: ctk.CTkComboBox | None = None
        self.backups_button: ctk.CTkButton | None = None
        self.documentation_button: ctk.CTkButton | None = None
        self.refresh_button: ctk.CTkButton | None = None
        self.export_changes_button: ctk.CTkButton | None = None
        self.review_export_queue_button: ctk.CTkButton | None = None
        self.add_tag_button: ctk.CTkButton | None = None
        self.find_replace_button: ctk.CTkButton | None = None
        self.find_replace_apply_button: ctk.CTkButton | None = None
        self.find_replace_delete_button: ctk.CTkButton | None = None
        self.find_replace_clear_button: ctk.CTkButton | None = None
        self.find_scope_combo: ctk.CTkComboBox | None = None
        self.find_replace_bar: ctk.CTkFrame | None = None
        self.filter_frame: ctk.CTkFrame | None = None
        self._find_replace_visible = True
        self.reset_filter_button: ctk.CTkButton | None = None
        self.change_tag_button: ctk.CTkButton | None = None
        self.vessel_combo: ctk.CTkComboBox | None = None
        self.tree = None
        self.context_menu: tk.Menu | None = None

        self._neutral_btn = button_neutral_kwargs()
        self._accent_btn = button_accent_kwargs()
        self._warning_btn = button_warning_kwargs()
        self._build_layout()

    def _build_layout(self) -> None:
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(main, text="Tag Central", font=FONT_TITLE, anchor="w").pack(
            anchor="w"
        )
        ctk.CTkLabel(
            main,
            text="Synchronize, review, and export vessel tag changes.",
            font=FONT_SUBTITLE,
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(2, 12))

        toolbar_row1 = ctk.CTkFrame(main, fg_color="transparent")
        toolbar_row1.pack(fill="x", pady=(0, 6))
        toolbar_row2 = ctk.CTkFrame(main, fg_color="transparent")
        toolbar_row2.pack(fill="x", pady=(0, 8))

        self.import_proficy_button = ctk.CTkButton(
            toolbar_row1, text="Import Proficy", **self._neutral_btn
        )
        self.import_cimplicity_button = ctk.CTkButton(
            toolbar_row1, text="Import Cimplicity", **self._neutral_btn
        )
        self.import_button = self.import_proficy_button
        self.cimplicity_review_button = ctk.CTkButton(
            toolbar_row1, text="Cimplicity Review (0)", **self._neutral_btn
        )
        self.cimplicity_tasks_button = ctk.CTkButton(
            toolbar_row1, text="Cimplicity Tasks (0)", **self._neutral_btn
        )
        self.refresh_button = ctk.CTkButton(
            toolbar_row1, text="Refresh", width=90, **self._neutral_btn
        )

        self.import_proficy_button.pack(side="left", padx=(0, 6))
        self.import_cimplicity_button.pack(side="left", padx=6)
        self.refresh_button.pack(side="left", padx=6)
        self.cimplicity_review_button.pack(side="left", padx=6)
        self.cimplicity_tasks_button.pack(side="left", padx=6)

        self.export_changes_button = ctk.CTkButton(
            toolbar_row2, text="Export Proficy Changes (0)", **self._accent_btn
        )
        self.review_export_queue_button = ctk.CTkButton(
            toolbar_row2, text="Review Export Queue", **self._neutral_btn
        )
        self.backups_button = ctk.CTkButton(
            toolbar_row2, text="Backups", width=90, **self._neutral_btn
        )
        self.documentation_button = ctk.CTkButton(
            toolbar_row2, text="Documentation", **self._neutral_btn
        )
        self.add_tag_button = ctk.CTkButton(
            toolbar_row2, text="Add Tag", width=90, **self._neutral_btn
        )
        self.find_replace_button = ctk.CTkButton(
            toolbar_row2, text="Find & Replace ▾", **self._neutral_btn
        )
        self.change_tag_button = ctk.CTkButton(
            toolbar_row2, text="Edit Selected Tag", **self._neutral_btn
        )

        self.export_changes_button.pack(side="left", padx=(0, 6))
        self.review_export_queue_button.pack(side="left", padx=6)
        self.backups_button.pack(side="left", padx=6)
        self.documentation_button.pack(side="left", padx=6)
        self.add_tag_button.pack(side="left", padx=6)
        self.find_replace_button.pack(side="left", padx=6)
        self.change_tag_button.pack(side="left", padx=6)

        self.find_replace_bar = ctk.CTkFrame(main, corner_radius=CORNER_RADIUS)
        self.find_replace_bar.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(
            self.find_replace_bar,
            text="Find & Replace",
            font=(FONT_BODY[0], FONT_BODY[1], "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        find_row = ctk.CTkFrame(self.find_replace_bar, fg_color="transparent")
        find_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(find_row, text="Find", font=FONT_SMALL).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(find_row, textvariable=self.find_text_var, width=180).pack(
            side="left", padx=(0, 10)
        )
        ctk.CTkLabel(find_row, text="Replace", font=FONT_SMALL).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkEntry(find_row, textvariable=self.replace_text_var, width=180).pack(
            side="left", padx=(0, 10)
        )
        ctk.CTkLabel(find_row, text="Scope", font=FONT_SMALL).pack(
            side="left", padx=(0, 6)
        )
        self.find_scope_combo = ctk.CTkComboBox(
            find_row,
            variable=self.find_scope_var,
            values=("tag", "description", "both"),
            state="readonly",
            width=120,
        )
        self.find_scope_combo.pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            find_row,
            text="Preview Changes",
            variable=self.preview_changes_var,
            font=FONT_SMALL,
        ).pack(side="left", padx=(0, 10))
        self.find_replace_apply_button = ctk.CTkButton(
            find_row, text="Apply", width=80, **self._accent_btn
        )
        self.find_replace_apply_button.pack(side="left", padx=(0, 6))
        self.find_replace_delete_button = ctk.CTkButton(
            find_row, text="Delete Matches", width=120, **self._neutral_btn
        )
        self.find_replace_delete_button.pack(side="left", padx=6)
        self.find_replace_clear_button = ctk.CTkButton(
            find_row, text="Clear", width=80, **self._neutral_btn
        )
        self.find_replace_clear_button.pack(side="left", padx=6)
        ctk.CTkLabel(
            find_row,
            textvariable=self.find_replace_status_var,
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(side="right", padx=(6, 0))

        self.filter_frame = ctk.CTkFrame(main, corner_radius=CORNER_RADIUS)
        self.filter_frame.pack(fill="x", pady=(4, 10))

        filter_inner = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        filter_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(filter_inner, text="Vessel", font=FONT_SMALL).pack(
            side="left", padx=(0, 8)
        )
        self.vessel_combo = ctk.CTkComboBox(
            filter_inner,
            variable=self.vessel_var,
            values=["ALL"],
            state="readonly",
            width=180,
        )
        self.vessel_combo.pack(side="left", padx=(0, 8))
        self.reset_filter_button = ctk.CTkButton(
            filter_inner, text="Reset Filter", width=100, **self._neutral_btn
        )
        self.reset_filter_button.pack(side="left", padx=(0, 18))

        ctk.CTkLabel(filter_inner, text="Program", font=FONT_SMALL).pack(
            side="left", padx=(0, 8)
        )
        self.program_filter_combo = ctk.CTkComboBox(
            filter_inner,
            variable=self.program_filter_var,
            values=PROGRAM_FILTER_VALUES,
            state="readonly",
            width=140,
        )
        self.program_filter_combo.pack(side="left", padx=(0, 18))

        ctk.CTkLabel(filter_inner, text="Search", font=FONT_SMALL).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(filter_inner, textvariable=self.search_var, width=220).pack(
            side="left", padx=(0, 8)
        )
        self.view_conflicts_check = ctk.CTkCheckBox(
            filter_inner,
            text="View Internal Mismatches (0)",
            variable=self.view_conflicts_var,
            font=FONT_SMALL,
        )
        self.view_conflicts_check.pack(side="left", padx=(8, 6))
        self.array_expand_toggle_button = ctk.CTkButton(
            filter_inner,
            text="Expand All",
            width=110,
            **self._neutral_btn,
        )
        self.array_expand_toggle_button.pack(side="left")

        table_frame = ctk.CTkFrame(main, corner_radius=CORNER_RADIUS)
        table_frame.pack(fill="both", expand=True, pady=(0, 4))
        self.tree, _y_scroll = create_tag_treeview(table_frame, height=16)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edit Tag")
        self.context_menu.add_command(label="Copy Tag")
        self.context_menu.add_command(label="Align to Cimplicity")
        self.context_menu.add_command(label="Toggle Array Indices", state="disabled")
        self.context_menu.add_command(label="Jump to Mismatches", state="disabled")
        self.context_menu.add_command(label="View Tag Diff", state="disabled")
        self.context_menu.add_command(label="Increment descriptions", state="disabled")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Merge Tags…", state="disabled")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Add Tag")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Tag")

        ctk.CTkLabel(
            main,
            textvariable=self.status_var,
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

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
            if count > 0:
                self.cimplicity_tasks_button.configure(**self._warning_btn)
            else:
                self.cimplicity_tasks_button.configure(**self._neutral_btn)

    def set_conflict_count(self, count: int) -> None:
        if self.view_conflicts_check is not None:
            self.view_conflicts_check.configure(
                text=f"View Internal Mismatches ({count})"
            )

    def set_pending_change_count(self, count: int) -> None:
        if self.export_changes_button is None:
            return
        self.export_changes_button.configure(text=f"Export Proficy Changes ({count})")
        if count > 0:
            self.export_changes_button.configure(**self._warning_btn)
        else:
            self.export_changes_button.configure(**self._accent_btn)

    def set_find_replace_status(
        self,
        *,
        find_active: bool,
        match_count: int,
        change_count: int,
        preview_on: bool,
    ) -> None:
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
        if (
            self.find_replace_bar is None
            or self.find_replace_button is None
            or self.filter_frame is None
        ):
            return
        if self._find_replace_visible:
            self.find_replace_bar.pack_forget()
            self.find_replace_button.configure(text="Find & Replace ▸")
            self._find_replace_visible = False
            return
        self.find_replace_bar.pack(fill="x", pady=(4, 8), before=self.filter_frame)
        self.find_replace_button.configure(text="Find & Replace ▾")
        self._find_replace_visible = True
