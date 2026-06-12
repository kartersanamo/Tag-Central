"""Dialog for creating a new tag."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.tag_form_dialog import VesselListEditor


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
        for row, (label, var) in enumerate(
            (
                ("Tag", self._tag_var),
                ("Description", self._description_var),
                ("Address", self._address_var),
            )
        ):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 8))
            ttk.Entry(form, textvariable=var, width=52).grid(
                row=row, column=1, sticky="ew", pady=(0, 8)
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
        self._vessel_editor = VesselListEditor(vessel_frame, vessels)
        self._vessel_editor.pack(fill="both", expand=True)

        actions = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Create", command=self._save).pack(side="right", padx=(0, 8))

    def _save(self) -> None:
        self._result = {
            "tag_name": self._tag_var.get().strip().upper(),
            "description": self._description_var.get().strip().upper(),
            "address": self._address_var.get().strip().upper(),
            "program": self._program_var.get().strip().lower(),
            "queue_proficy": bool(self._queue_var.get()),
            "vessels": self._vessel_editor.vessel_names(),
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
