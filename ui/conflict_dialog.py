"""UI dialog for tag import conflicts."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ConflictDialog:
    """Collects user decision when an imported row conflicts."""

    def __init__(
        self,
        parent: tk.Tk,
        vessel: str,
        imported_tag: str,
        imported_description: str,
        existing_tag: str,
        existing_description: str,
    ) -> None:
        self._result = {"action": "skip"}
        self._window = tk.Toplevel(parent)
        self._window.title("Resolve Tag Conflict")
        self._window.geometry("760x430")
        self._window.transient(parent)
        self._window.grab_set()

        self._build_ui(
            vessel=vessel,
            imported_tag=imported_tag,
            imported_description=imported_description,
            existing_tag=existing_tag,
            existing_description=existing_description,
        )

    def show(self) -> dict[str, str]:
        """Shows the dialog and returns selected conflict action."""
        self._window.wait_window()
        return self._result

    def _build_ui(
        self,
        vessel: str,
        imported_tag: str,
        imported_description: str,
        existing_tag: str,
        existing_description: str,
    ) -> None:
        header = (
            f"Vessel '{vessel}' has a conflict.\n"
            "Choose how to map the imported row into the master database."
        )
        ttk.Label(self._window, text=header, justify="left").pack(
            fill="x", padx=16, pady=(14, 10)
        )

        panel = ttk.Frame(self._window, padding=14)
        panel.pack(fill="both", expand=True)

        imported_box = ttk.LabelFrame(panel, text="Imported")
        existing_box = ttk.LabelFrame(panel, text="Existing")
        imported_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        existing_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

        ttk.Label(imported_box, text=f"Tag: {imported_tag}").pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ttk.Label(imported_box, text=f"Description: {imported_description}").pack(
            anchor="w", padx=12, pady=(0, 12)
        )
        ttk.Label(existing_box, text=f"Tag: {existing_tag}").pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ttk.Label(existing_box, text=f"Description: {existing_description}").pack(
            anchor="w", padx=12, pady=(0, 12)
        )

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")

        ttk.Button(
            button_bar,
            text="Use Imported Tag",
            command=lambda: self._close(
                action="use_imported",
                resolved_tag=imported_tag,
                resolved_description=imported_description,
            ),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            button_bar,
            text="Use Existing Tag",
            command=lambda: self._close(
                action="use_existing",
                resolved_tag=existing_tag,
                resolved_description=existing_description,
            ),
        ).pack(side="left", padx=8)

        ttk.Button(
            button_bar,
            text="Keep Both (Suffix Imported)",
            command=lambda: self._close(
                action="keep_both",
                resolved_tag=imported_tag,
                resolved_description=imported_description,
            ),
        ).pack(side="left", padx=8)

        ttk.Button(
            button_bar,
            text="Skip Row",
            command=lambda: self._close(action="skip"),
        ).pack(side="right")

    def _close(self, **result: str) -> None:
        self._result = result
        self._window.destroy()
