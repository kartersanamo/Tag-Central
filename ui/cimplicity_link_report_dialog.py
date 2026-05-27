"""Post-import Cimplicity link statistics."""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk


class CimplicityLinkReportDialog:
    """Shows how Cimplicity rows were linked during import."""

    def __init__(self, parent: tk.Tk, lines: list[str], apply_summary: list[str]) -> None:
        self._window = tk.Toplevel(parent)
        self._window.title("Cimplicity Link Report")
        self._window.geometry("640x520")
        self._window.transient(parent)

        ttk.Label(
            self._window,
            text="Cimplicity import link breakdown",
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        text = scrolledtext.ScrolledText(self._window, height=24, wrap="word")
        text.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        body = "\n".join(lines)
        if apply_summary:
            body += "\n\n--- Apply results ---\n" + "\n".join(apply_summary)
        text.insert("1.0", body)
        text.configure(state="disabled")

        ttk.Button(self._window, text="Close", command=self._window.destroy).pack(
            pady=(0, 14)
        )
