"""Dialog for editing tag details."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog

import customtkinter as ctk

from ui.ctk_theme import FONT_BODY, button_accent_kwargs, button_neutral_kwargs


class EditTagDialog:
    """Edits tag name, description, and vessel membership."""

    def __init__(
        self,
        parent: ctk.CTk,
        tag_name: str,
        description: str,
        address: str,
        vessels: set[str],
    ) -> None:
        self._result: dict[str, object] | None = None
        self._window = ctk.CTkToplevel(parent)
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
        form = ctk.CTkFrame(self._window, fg_color="transparent")
        form.pack(fill="x", padx=14, pady=14)
        for row, (label, var) in enumerate(
            (
                ("Tag", self._tag_var),
                ("Description", self._description_var),
                ("Address", self._address_var),
            )
        ):
            ctk.CTkLabel(form, text=label, font=FONT_BODY).grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            ctk.CTkEntry(form, textvariable=var, width=360).grid(
                row=row, column=1, sticky="ew", pady=(0, 8)
            )
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
            actions, text="Save", command=self._save, **button_accent_kwargs()
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
            "vessels": vessels,
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
