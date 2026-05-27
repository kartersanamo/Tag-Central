"""Pre-import summary before applying Proficy or Cimplicity data."""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk


class ImportDryRunDialog:
    """Shows import analysis and returns whether user chose Apply."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        summary_lines: list[str],
    ) -> None:
        self._result = False
        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.geometry("620x480")
        self._window.transient(parent)
        self._window.grab_set()

        ttk.Label(
            self._window,
            text="Review the import summary, then apply or cancel.",
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        text = scrolledtext.ScrolledText(self._window, height=20, wrap="word")
        text.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        text.insert("1.0", "\n".join(summary_lines))
        text.configure(state="disabled")

        buttons = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Apply Import", command=self._apply).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")

        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

    def _apply(self) -> None:
        self._result = True
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = False
        self._window.destroy()

    def show(self) -> bool:
        self._window.wait_window()
        return self._result
