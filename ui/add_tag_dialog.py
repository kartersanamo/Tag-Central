"""Dialog for creating a new tag."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog

import customtkinter as ctk

from ui.ctk_theme import FONT_BODY, button_accent_kwargs, button_neutral_kwargs


class AddTagDialog:
    """Collects new-tag fields, program target, and queue behavior."""

    def __init__(self, parent: ctk.CTk, vessels: list[str]) -> None:
        self._result: dict[str, object] | None = None
        self._window = ctk.CTkToplevel(parent)
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
        form = ctk.CTkFrame(self._window, fg_color="transparent")
        form.pack(fill="x", padx=14, pady=14)

        labels = ("Tag", "Description", "Address", "Program")
        vars_ = (
            self._tag_var,
            self._description_var,
            self._address_var,
            self._program_var,
        )
        for row, (label, var) in enumerate(zip(labels, vars_)):
            ctk.CTkLabel(form, text=label, font=FONT_BODY).grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            if label == "Program":
                ctk.CTkComboBox(
                    form,
                    variable=var,
                    values=("proficy", "cimplicity", "both"),
                    state="readonly",
                    width=180,
                ).grid(row=row, column=1, sticky="w", pady=(0, 8))
            else:
                ctk.CTkEntry(form, textvariable=var, width=400).grid(
                    row=row, column=1, sticky="ew", pady=(0, 8)
                )
        ctk.CTkCheckBox(
            form,
            text="Queue Proficy export row (when Proficy is selected)",
            variable=self._queue_var,
            font=FONT_BODY,
        ).grid(row=4, column=1, sticky="w", pady=(2, 0))
        form.columnconfigure(1, weight=1)

        vessel_frame = ctk.CTkFrame(self._window)
        vessel_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        ctk.CTkLabel(
            vessel_frame, text="Vessels", font=(FONT_BODY[0], FONT_BODY[1], "bold")
        ).pack(anchor="w", padx=10, pady=(10, 6))

        list_row = ctk.CTkFrame(vessel_frame, fg_color="transparent")
        list_row.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._vessel_list = tk.Listbox(list_row, selectmode="extended", height=12)
        self._vessel_list.pack(fill="both", expand=True, side="left")
        for vessel in vessels:
            self._vessel_list.insert("end", vessel)

        button_column = ctk.CTkFrame(list_row, fg_color="transparent")
        button_column.pack(side="left", fill="y", padx=(8, 0))
        ctk.CTkButton(
            button_column, text="Add Vessel", command=self._add_vessel, **button_neutral_kwargs()
        ).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            button_column,
            text="Remove Selected",
            command=self._remove_selected,
            **button_neutral_kwargs(),
        ).pack(fill="x")

        actions = ctk.CTkFrame(self._window, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(actions, text="Cancel", command=self._cancel, **button_neutral_kwargs()).pack(
            side="right"
        )
        ctk.CTkButton(
            actions, text="Create", command=self._save, **button_accent_kwargs()
        ).pack(side="right", padx=(0, 8))

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
