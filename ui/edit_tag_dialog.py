"""Dialog for editing tag details."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.tag_form_dialog import VesselListEditor


class EditTagDialog:
    """Edits tag name, description, and vessel membership."""

    def __init__(
        self,
        parent: tk.Tk,
        tag_name: str,
        description: str,
        address: str,
        vessels: set[str],
    ) -> None:
        self._result: dict[str, object] | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Edit Tag")
        self._window.geometry("560x480")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        self._tag_var = tk.StringVar(value=tag_name)
        self._description_var = tk.StringVar(value=description)
        self._address_var = tk.StringVar(value=address)
        self._build_ui(sorted(vessels))

    def show(self) -> dict[str, object] | None:
        self._window.wait_window()
        return self._result

    def _build_ui(self, vessels: list[str]) -> None:
        form = ttk.Frame(self._window, padding=14)
        form.pack(fill="x")
        for row, (label, var) in enumerate(
            (
                ("Tag", self._tag_var),
                ("Description", self._description_var),
                ("Address", self._address_var),
            )
        ):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 8))
            ttk.Entry(form, textvariable=var, width=48).grid(
                row=row, column=1, sticky="ew", pady=(0, 8)
            )
        form.columnconfigure(1, weight=1)

        vessel_frame = ttk.LabelFrame(self._window, text="Vessels", padding=10)
        vessel_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._vessel_editor = VesselListEditor(vessel_frame, vessels)
        self._vessel_editor.pack(fill="both", expand=True)

        actions = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Save", command=self._save).pack(side="right", padx=(0, 8))

    def _save(self) -> None:
        self._result = {
            "tag_name": self._tag_var.get().strip().upper(),
            "description": self._description_var.get().strip().upper(),
            "address": self._address_var.get().strip().upper(),
            "vessels": self._vessel_editor.vessel_names(),
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
