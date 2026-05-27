"""Dialog for creating a new tag."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk


class AddTagDialog:
    """Collects new-tag fields, program target, and queue behavior."""

    def __init__(self, parent: tk.Tk, vessels: list[str]) -> None:
        self._result: dict[str, object] | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Add Tag")
        self._window.geometry("620x540")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        self._tag_var = tk.StringVar()
        self._description_var = tk.StringVar()
        self._address_var = tk.StringVar()
        self._program_var = tk.StringVar(value="proficy")
        self._queue_var = tk.BooleanVar(value=True)
        self._build_ui(vessels)

    def show(self) -> dict[str, object] | None:
        self._window.wait_window()
        return self._result

    def _build_ui(self, vessels: list[str]) -> None:
        form = ttk.Frame(self._window, padding=14)
        form.pack(fill="x")

        ttk.Label(form, text="Tag").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self._tag_var, width=52).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self._description_var, width=52).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Label(form, text="Address").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self._address_var, width=52).grid(
            row=2, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Label(form, text="Program").grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            form,
            textvariable=self._program_var,
            values=("proficy", "cimplicity", "both"),
            state="readonly",
            width=18,
        ).grid(row=3, column=1, sticky="w", pady=(0, 8))
        ttk.Checkbutton(
            form,
            text="Queue Proficy export row (when Proficy is selected)",
            variable=self._queue_var,
        ).grid(row=4, column=1, sticky="w", pady=(2, 0))
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
        ttk.Button(actions, text="Create", command=self._save).pack(side="right", padx=(0, 8))

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
            "address": self._address_var.get().strip().upper(),
            "program": self._program_var.get().strip().lower(),
            "queue_proficy": bool(self._queue_var.get()),
            "vessels": vessels,
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
