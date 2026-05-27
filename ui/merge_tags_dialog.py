"""Pick survivor tag when merging two records."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class MergeTagsDialog:
    """Returns the canonical tag name to keep after merge."""

    def __init__(self, parent: tk.Tk, tag_a: str, tag_b: str) -> None:
        self._result: str | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Merge Tags")
        self._window.geometry("480x220")
        self._window.transient(parent)
        self._window.grab_set()

        self._choice = tk.StringVar(value=tag_a)
        ttk.Label(
            self._window,
            text="Select which tag survives. The other will be removed.",
            wraplength=440,
        ).pack(anchor="w", padx=14, pady=(14, 10))

        ttk.Radiobutton(self._window, text=tag_a, variable=self._choice, value=tag_a).pack(
            anchor="w", padx=20
        )
        ttk.Radiobutton(self._window, text=tag_b, variable=self._choice, value=tag_b).pack(
            anchor="w", padx=20, pady=(4, 0)
        )

        buttons = ttk.Frame(self._window, padding=14)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Merge", command=self._confirm).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")

    def _confirm(self) -> None:
        self._result = self._choice.get().strip().upper()
        if not self._result:
            messagebox.showwarning("Invalid", "Select a survivor tag.")
            return
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()

    def show(self) -> str | None:
        self._window.wait_window()
        return self._result
