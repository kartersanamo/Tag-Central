"""Configurable bulk-action resolver dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class BulkResolverDialog:
    """Table of rows with bulk action assignment and apply/cancel."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        *,
        columns: tuple[str, ...],
        headings: dict[str, str],
        widths: dict[str, int],
        actions: tuple[str, ...],
        width: int = 1300,
        height: int = 720,
    ) -> None:
        self._result: list[dict[str, str]] | None = None
        self._decision_var = tk.StringVar(value="pending")
        self._rows: list[dict[str, str]] = []
        self._columns = columns
        self._actions = actions
        self._row_values: Callable[[dict[str, str]], tuple[str, ...]] | None = None
        self._bulk_buttons: list[tuple[str, str]] = []

        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.geometry(f"{width}x{height}")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._header_var = tk.StringVar()
        self._status_var = tk.StringVar()
        self._selected_action_var = tk.StringVar(value=actions[0] if actions else "")

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
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="extended"
        )
        for col in columns:
            self._tree.heading(col, text=headings.get(col, col))
            self._tree.column(col, width=widths.get(col, 120), anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        self._button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        self._button_bar.pack(fill="x")
        ttk.Label(self._button_bar, text="Set selected rows to:").pack(side="left")
        ttk.Combobox(
            self._button_bar,
            textvariable=self._selected_action_var,
            state="readonly",
            values=actions,
            width=20,
        ).pack(side="left", padx=(8, 8))
        ttk.Button(
            self._button_bar, text="Apply To Selected", command=self._apply_selected
        ).pack(side="left", padx=(0, 16))
        ttk.Button(self._button_bar, text="Cancel Import", command=self._on_close).pack(
            side="right"
        )
        ttk.Button(self._button_bar, text="Apply Decisions", command=self._submit).pack(
            side="right", padx=(0, 8)
        )

    def configure_row_mapper(
        self, mapper: Callable[[dict[str, str]], tuple[str, ...]]
    ) -> None:
        self._row_values = mapper

    def add_bulk_button(self, label: str, action: str) -> None:
        self._bulk_buttons.append((label, action))
        ttk.Button(
            self._button_bar,
            text=label,
            command=lambda value=action: self._apply_all(value),
        ).pack(side="left", padx=4)

    def set_status_formatter(
        self, formatter: Callable[[list[dict[str, str]]], str]
    ) -> None:
        self._status_formatter = formatter

    def resolve(
        self,
        header: str,
        rows: list[dict[str, str]],
        *,
        default_action: str = "skip",
        action_key: str = "action",
    ) -> list[dict[str, str]] | None:
        self._result = None
        self._decision_var.set("pending")
        self._action_key = action_key
        self._rows = [dict(row) for row in rows]
        for row in self._rows:
            row.setdefault(action_key, row.get("default_action", default_action))
        self._header_var.set(header)
        self._render()
        self._refresh_status()
        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._window.wait_variable(self._decision_var)
        return self._result

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        if self._row_values is None:
            return
        for index, row in enumerate(self._rows):
            self._tree.insert("", "end", iid=str(index), values=self._row_values(row))

    def _apply_selected(self) -> None:
        action = self._selected_action_var.get()
        for item in self._tree.selection():
            self._rows[int(item)][self._action_key] = action
        self._render()
        self._refresh_status()

    def _apply_all(self, action: str) -> None:
        for row in self._rows:
            row[self._action_key] = action
        self._render()
        self._refresh_status()

    def _submit(self) -> None:
        self._result = self._rows
        self._decision_var.set("done")

    def _refresh_status(self) -> None:
        if hasattr(self, "_status_formatter"):
            self._status_var.set(self._status_formatter(self._rows))
        else:
            counts: dict[str, int] = {}
            for row in self._rows:
                action = row.get(self._action_key, "skip")
                counts[action] = counts.get(action, 0) + 1
            self._status_var.set(
                " | ".join(f"{action}: {counts[action]}" for action in sorted(counts))
            )

    def _on_close(self) -> None:
        self._result = None
        self._decision_var.set("done")

    def close(self) -> None:
        if self._window.winfo_exists():
            self._window.destroy()
