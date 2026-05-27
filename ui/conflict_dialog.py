"""UI dialog for tag import conflicts."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ConflictDialog:
    """Collects user decision when an imported row conflicts."""

    def __init__(self, parent: tk.Tk) -> None:
        self._result: dict[str, str] = {"action": "skip"}
        self._decision_var = tk.StringVar(value="")
        self._window = tk.Toplevel(parent)
        self._window.title("Resolve Tag Conflict")
        self._window.geometry("760x430")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._header_var = tk.StringVar(value="")
        self._progress_var = tk.StringVar(value="")
        self._imported_tag_var = tk.StringVar(value="")
        self._imported_description_var = tk.StringVar(value="")
        self._existing_tag_var = tk.StringVar(value="")
        self._existing_description_var = tk.StringVar(value="")

        self._build_ui()

    def resolve_conflict(
        self,
        vessel: str,
        imported_tag: str,
        imported_description: str,
        existing_tag: str,
        existing_description: str,
        remaining_conflicts: int,
        total_conflicts: int,
    ) -> dict[str, str]:
        """Shows updated conflict content and waits for user decision."""
        self._result = {"action": "skip"}
        self._decision_var.set("")

        self._header_var.set(
            f"Vessel '{vessel}' has a conflict. Choose how to map this row."
        )
        self._progress_var.set(
            f"Conflicts remaining: {remaining_conflicts} of {total_conflicts}"
        )
        self._imported_tag_var.set(imported_tag)
        self._imported_description_var.set(imported_description)
        self._existing_tag_var.set(existing_tag)
        self._existing_description_var.set(existing_description)

        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._window.wait_variable(self._decision_var)
        return self._result

    def close(self) -> None:
        """Destroys the dialog window after the import session."""
        if self._window.winfo_exists():
            self._window.destroy()

    def _build_ui(self) -> None:
        ttk.Label(self._window, textvariable=self._header_var, justify="left").pack(
            fill="x", padx=16, pady=(14, 10)
        )
        ttk.Label(
            self._window,
            textvariable=self._progress_var,
            foreground="#0f4c81",
            font=("Helvetica", 11, "bold"),
        ).pack(fill="x", padx=16, pady=(0, 8))

        panel = ttk.Frame(self._window, padding=14)
        panel.pack(fill="both", expand=True)

        imported_box = ttk.LabelFrame(panel, text="Imported")
        existing_box = ttk.LabelFrame(panel, text="Existing")
        imported_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        existing_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

        ttk.Label(imported_box, textvariable=self._imported_tag_var).pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ttk.Label(imported_box, textvariable=self._imported_description_var).pack(
            anchor="w", padx=12, pady=(0, 12)
        )
        ttk.Label(existing_box, textvariable=self._existing_tag_var).pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ttk.Label(existing_box, textvariable=self._existing_description_var).pack(
            anchor="w", padx=12, pady=(0, 12)
        )

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")

        ttk.Button(
            button_bar,
            text="Use Imported Tag",
            command=lambda: self._close(action="use_imported"),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            button_bar,
            text="Use Existing Tag",
            command=lambda: self._close(action="use_existing"),
        ).pack(side="left", padx=8)

        ttk.Button(
            button_bar,
            text="Keep Both (Suffix Imported)",
            command=lambda: self._close(action="keep_both"),
        ).pack(side="left", padx=8)

        ttk.Button(
            button_bar,
            text="Skip Row",
            command=lambda: self._close(action="skip"),
        ).pack(side="right")

    def _close(self, **result: str) -> None:
        self._result = result
        self._decision_var.set("done")

    def _on_window_close(self) -> None:
        self._result = {"action": "skip"}
        self._decision_var.set("done")
