"""Dialog for global find and replace operations."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class FindReplaceDialog:
    """Collects find/replace input and target scope."""

    def __init__(self, parent: tk.Tk) -> None:
        self._result: dict[str, str] | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Find & Replace")
        self._window.geometry("640x420")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.scope_var = tk.StringVar(value="both")

        self._build_ui()

    def show(self) -> dict[str, str] | None:
        """Shows modal dialog and returns selected operation."""
        self._window.wait_window()
        return self._result

    def _build_ui(self) -> None:
        container = ttk.Frame(self._window, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Find & Replace", font=("Helvetica", 15, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            container,
            text="Apply text replacement across tags, descriptions, or both.",
        ).pack(anchor="w", pady=(4, 14))

        form = ttk.Frame(container)
        form.pack(fill="x")
        ttk.Label(form, text="Find").grid(row=0, column=0, sticky="w", pady=(0, 10))
        ttk.Entry(form, textvariable=self.find_var, width=54).grid(
            row=0, column=1, sticky="ew", pady=(0, 10)
        )
        ttk.Label(form, text="Replace With").grid(row=1, column=0, sticky="w", pady=(0, 10))
        ttk.Entry(form, textvariable=self.replace_var, width=54).grid(
            row=1, column=1, sticky="ew", pady=(0, 10)
        )
        form.columnconfigure(1, weight=1)

        scope_box = ttk.LabelFrame(container, text="Apply To", padding=10)
        scope_box.pack(fill="x", pady=(8, 10))
        ttk.Radiobutton(scope_box, text="Tag", variable=self.scope_var, value="tag").pack(
            anchor="w"
        )
        ttk.Radiobutton(
            scope_box, text="Description", variable=self.scope_var, value="description"
        ).pack(anchor="w")
        ttk.Radiobutton(scope_box, text="Both", variable=self.scope_var, value="both").pack(
            anchor="w"
        )

        note = ttk.Label(
            container,
            text=(
                "Tip: replacement is case-insensitive and updates matching text segments. "
                "Changes are autosaved and added to pending export batches."
            ),
            foreground="#4b5563",
            wraplength=600,
            justify="left",
        )
        note.pack(anchor="w", pady=(4, 16))

        actions = ttk.Frame(container)
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Apply", command=self._apply).pack(side="right", padx=(0, 8))

    def _apply(self) -> None:
        self._result = {
            "find_text": self.find_var.get(),
            "replace_text": self.replace_var.get(),
            "scope": self.scope_var.get(),
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
