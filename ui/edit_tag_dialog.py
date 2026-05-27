"""Dialog for editing tag details."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk


class EditTagDialog:
    """Edits tag name, description, and vessel membership."""

    def __init__(
        self,
        parent: tk.Tk,
        tag_name: str,
        description: str,
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
        self._build_ui(sorted(vessels))

    def show(self) -> dict[str, object] | None:
        """Returns edited values, or None when cancelled."""
        self._window.wait_window()
        return self._result

    def _build_ui(self, vessels: list[str]) -> None:
        form = ttk.Frame(self._window, padding=14)
        form.pack(fill="x")
        ttk.Label(form, text="Tag").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self._tag_var, width=48).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self._description_var, width=48).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )
        form.columnconfigure(1, weight=1)

        vessel_frame = ttk.LabelFrame(self._window, text="Vessels", padding=10)
        vessel_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._vessel_list = tk.Listbox(vessel_frame, selectmode="extended", height=12)
        self._vessel_list.pack(fill="both", expand=True, side="left")
        for vessel in vessels:
            self._vessel_list.insert("end", vessel)

        button_column = ttk.Frame(vessel_frame)
        button_column.pack(side="left", fill="y", padx=(8, 0))
        ttk.Button(button_column, text="Add Vessel", command=self._add_vessel).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(button_column, text="Remove Selected", command=self._remove_selected).pack(
            fill="x"
        )

        actions = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Save", command=self._save).pack(side="right", padx=(0, 8))

    def _add_vessel(self) -> None:
        vessel = simpledialog.askstring("Add Vessel", "Vessel name:", parent=self._window)
        if not vessel:
            return
        vessel = vessel.strip().upper()
        if not vessel:
            return
        existing = {self._vessel_list.get(index) for index in range(self._vessel_list.size())}
        if vessel in existing:
            return
        self._vessel_list.insert("end", vessel)

    def _remove_selected(self) -> None:
        for index in reversed(self._vessel_list.curselection()):
            self._vessel_list.delete(index)

    def _save(self) -> None:
        vessels = {
            self._vessel_list.get(index).strip().upper()
            for index in range(self._vessel_list.size())
            if self._vessel_list.get(index).strip()
        }
        self._result = {
            "tag_name": self._tag_var.get().strip().upper(),
            "description": self._description_var.get().strip().upper(),
            "vessels": vessels,
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
