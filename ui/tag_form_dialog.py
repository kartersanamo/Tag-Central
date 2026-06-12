"""Shared vessel list editor for tag forms."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk


class VesselListEditor(ttk.Frame):
    """Listbox of vessel names with add/remove controls."""

    def __init__(self, parent: tk.Widget, vessels: list[str]) -> None:
        super().__init__(parent)
        self._list = tk.Listbox(self, selectmode="extended", height=12)
        self._list.pack(fill="both", expand=True, side="left")
        for vessel in vessels:
            self._list.insert("end", vessel)

        column = ttk.Frame(self)
        column.pack(side="left", fill="y", padx=(8, 0))
        ttk.Button(column, text="Add Vessel", command=self._add_vessel).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(column, text="Remove Selected", command=self._remove_selected).pack(
            fill="x"
        )

    def _add_vessel(self) -> None:
        vessel = simpledialog.askstring(
            "Add Vessel", "Vessel name:", parent=self.winfo_toplevel()
        )
        if not vessel:
            return
        vessel = vessel.strip().upper()
        if not vessel:
            return
        existing = {self._list.get(i) for i in range(self._list.size())}
        if vessel in existing:
            return
        self._list.insert("end", vessel)

    def _remove_selected(self) -> None:
        for index in reversed(self._list.curselection()):
            self._list.delete(index)

    def vessel_names(self) -> set[str]:
        return {
            self._list.get(i).strip().upper()
            for i in range(self._list.size())
            if self._list.get(i).strip()
        }
