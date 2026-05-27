"""Dialog for reviewing rows missing descriptions."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class MissingDescriptionDialog:
    """Allows user review/edit for generated descriptions before import."""

    def __init__(
        self,
        parent: tk.Tk,
        candidates: list[dict[str, object]],
        *,
        title: str = "Review Missing Descriptions",
    ) -> None:
        self._candidates = candidates
        self._result: dict[int, str] | None = None
        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.geometry("980x620")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        self._description_var = tk.StringVar(value="")
        self._build_ui()

    def show(self) -> dict[int, str] | None:
        """Shows dialog and returns edited descriptions by row index."""
        self._window.wait_window()
        return self._result

    def _build_ui(self) -> None:
        header = ttk.Frame(self._window, padding=14)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Some rows are missing descriptions.",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Review suggested descriptions below, edit as needed, then continue.",
        ).pack(anchor="w", pady=(4, 0))

        table_frame = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table_frame.pack(fill="both", expand=True)
        self._tree = ttk.Treeview(
            table_frame,
            columns=("tag", "suggested", "final"),
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("tag", text="Tag")
        self._tree.heading("suggested", text="Suggested Description")
        self._tree.heading("final", text="Final Description")
        self._tree.column("tag", width=250, anchor="w")
        self._tree.column("suggested", width=320, anchor="w")
        self._tree.column("final", width=340, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        for candidate in self._candidates:
            row_index = int(candidate["row_index"])
            tag = str(candidate["tag"])
            suggested = str(candidate["suggested"])
            self._tree.insert(
                "",
                "end",
                iid=str(row_index),
                values=(tag, suggested, suggested),
            )

        editor = ttk.Frame(self._window, padding=(14, 0, 14, 12))
        editor.pack(fill="x")
        ttk.Label(editor, text="Edit selected final description:").pack(side="left")
        entry = ttk.Entry(editor, textvariable=self._description_var, width=78)
        entry.pack(side="left", padx=(10, 8), fill="x", expand=True)
        ttk.Button(editor, text="Apply", command=self._apply_selected_edit).pack(side="left")

        actions = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel Import", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Continue Import", command=self._continue_import).pack(
            side="right", padx=(0, 8)
        )

        self._tree.bind("<<TreeviewSelect>>", self._sync_editor_with_selection)
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._sync_editor_with_selection(None)

    def _sync_editor_with_selection(self, _: object) -> None:
        selection = self._tree.selection()
        if not selection:
            self._description_var.set("")
            return
        values = self._tree.item(selection[0], "values")
        self._description_var.set(str(values[2]))

    def _apply_selected_edit(self) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self._tree.item(item_id, "values")
        self._tree.item(item_id, values=(values[0], values[1], self._description_var.get().strip()))

    def _continue_import(self) -> None:
        result: dict[int, str] = {}
        for item_id in self._tree.get_children():
            values = self._tree.item(item_id, "values")
            result[int(item_id)] = str(values[2]).strip().upper()
        self._result = result
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
