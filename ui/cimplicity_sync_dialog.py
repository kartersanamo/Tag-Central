"""Bulk resolver for Cimplicity import sync actions."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class CimplicitySyncDialog:
    """Collects bulk decisions for Cimplicity-to-Proficy alignment."""

    ACTIONS = (
        "align_proficy",
        "link_only",
        "flag_manual_cimplicity",
        "skip",
    )

    def __init__(self, parent: tk.Tk) -> None:
        self._result: list[dict[str, str]] | None = None
        self._decision_var = tk.StringVar(value="pending")
        self._window = tk.Toplevel(parent)
        self._window.title("Cimplicity Sync Resolver")
        self._window.geometry("1400x720")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._header_var = tk.StringVar(value="")
        self._selected_action_var = tk.StringVar(value="align_proficy")
        self._status_var = tk.StringVar(value="")
        self._conflicts: list[dict[str, str]] = []
        self._build_ui()

    def resolve_rows(
        self, vessel: str, rows: list[dict[str, str]]
    ) -> list[dict[str, str]] | None:
        self._result = None
        self._decision_var.set("pending")
        self._conflicts = [dict(row) for row in rows]
        for row in self._conflicts:
            row.setdefault("action", row.get("default_action", "align_proficy"))
        self._header_var.set(
            f"Vessel '{vessel}': {len(rows)} rows need sync decisions. "
            "Default aligns Proficy to Cimplicity (recommended)."
        )
        self._render_rows()
        self._refresh_status()
        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._window.wait_variable(self._decision_var)
        return self._result

    def close(self) -> None:
        if self._window.winfo_exists():
            self._window.destroy()

    def _build_ui(self) -> None:
        ttk.Label(self._window, textvariable=self._header_var, justify="left").pack(
            fill="x", padx=16, pady=(14, 10)
        )
        ttk.Label(
            self._window,
            textvariable=self._status_var,
            foreground="#0f4c81",
            font=("Helvetica", 11, "bold"),
        ).pack(fill="x", padx=16, pady=(0, 8))

        table_frame = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table_frame.pack(fill="both", expand=True)
        columns = (
            "action",
            "pt_id",
            "cim_desc",
            "address",
            "existing_tag",
            "existing_desc",
            "issue",
        )
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="extended"
        )
        headings = {
            "action": "Action",
            "pt_id": "Cimplicity PT_ID",
            "cim_desc": "Cimplicity Description",
            "address": "Address",
            "existing_tag": "Proficy Tag",
            "existing_desc": "Current Description",
            "issue": "Issue",
        }
        widths = {
            "action": 170,
            "pt_id": 160,
            "cim_desc": 240,
            "address": 110,
            "existing_tag": 160,
            "existing_desc": 240,
            "issue": 180,
        }
        for column in columns:
            self._tree.heading(column, text=headings[column])
            self._tree.column(column, width=widths[column], anchor="w")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=y_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")
        ttk.Label(button_bar, text="Set selected rows to:").pack(side="left")
        ttk.Combobox(
            button_bar,
            textvariable=self._selected_action_var,
            state="readonly",
            values=self.ACTIONS,
            width=24,
        ).pack(side="left", padx=(8, 8))
        ttk.Button(button_bar, text="Apply To Selected", command=self._apply_selected).pack(
            side="left", padx=(0, 16)
        )
        ttk.Button(
            button_bar,
            text="Align Proficy For All",
            command=lambda: self._apply_all("align_proficy"),
        ).pack(side="left", padx=4)
        ttk.Button(
            button_bar, text="Skip All", command=lambda: self._apply_all("skip")
        ).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Cancel Import", command=self._on_window_close).pack(
            side="right"
        )
        ttk.Button(button_bar, text="Apply Decisions", command=self._submit).pack(
            side="right", padx=(0, 8)
        )

    def _render_rows(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, row in enumerate(self._conflicts):
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row.get("action", "align_proficy"),
                    row.get("pt_id", ""),
                    row.get("cimplicity_description", ""),
                    row.get("address", ""),
                    row.get("existing_tag", ""),
                    row.get("existing_description", ""),
                    row.get("issue", ""),
                ),
            )

    def _apply_selected(self) -> None:
        action = self._selected_action_var.get()
        for item in self._tree.selection():
            self._conflicts[int(item)]["action"] = action
        self._render_rows()
        self._refresh_status()

    def _apply_all(self, action: str) -> None:
        for row in self._conflicts:
            row["action"] = action
        self._render_rows()
        self._refresh_status()

    def _submit(self) -> None:
        self._result = self._conflicts
        self._decision_var.set("done")

    def _refresh_status(self) -> None:
        counts = {action: 0 for action in self.ACTIONS}
        for row in self._conflicts:
            counts[row.get("action", "skip")] = counts.get(row.get("action", "skip"), 0) + 1
        self._status_var.set(
            " · ".join(f"{action}: {counts[action]}" for action in self.ACTIONS)
        )

    def _on_window_close(self) -> None:
        self._result = None
        self._decision_var.set("done")
