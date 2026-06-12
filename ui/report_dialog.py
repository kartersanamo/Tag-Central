"""Read-only report dialog with optional apply/cancel."""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk


class ReportDialog:
    """Shows scrollable text with Close or Apply/Cancel actions."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        *,
        intro: str = "",
        width: int = 640,
        height: int = 480,
        apply_label: str | None = None,
    ) -> None:
        self._result = False
        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.geometry(f"{width}x{height}")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        if intro:
            ttk.Label(self._window, text=intro, font=("Helvetica", 11)).pack(
                anchor="w", padx=14, pady=(12, 8)
            )

        self._text = scrolledtext.ScrolledText(self._window, height=20, wrap="word")
        self._text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        buttons = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        buttons.pack(fill="x")
        if apply_label:
            ttk.Button(buttons, text=apply_label, command=self._apply).pack(side="left")
            ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        else:
            ttk.Button(buttons, text="Close", command=self._cancel).pack(side="right")

    def set_content(self, content: str) -> None:
        self._text.insert("1.0", content)
        self._text.configure(state="disabled")

    def _apply(self) -> None:
        self._result = True
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = False
        self._window.destroy()

    def show(self) -> bool:
        self._window.wait_window()
        return self._result

    def show_readonly(self) -> None:
        self._window.wait_window()
