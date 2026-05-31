"""Review and edit pending Proficy export queue entries."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Callable

import customtkinter as ctk

from services.export_queue_service import ExportQueueService, changed_field_labels
from ui.ctk_theme import FONT_BODY, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview


class ExportQueueDialog:
    """Lists pending export rows with per-row edit and remove."""

    def __init__(
        self,
        parent: ctk.CTk,
        queue: ExportQueueService,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._queue = queue
        self._on_change = on_change
        self._window = ctk.CTkToplevel(parent)
        self._window.title("Export Queue")
        self._window.geometry("1100x600")
        self._window.transient(parent)

        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text="Review pending Proficy export rows before running Export Changes.",
            font=FONT_BODY,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        table_frame = ctk.CTkFrame(body)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        self._tree, _scroll = create_data_treeview(
            table_frame,
            ("vessel", "tag", "changed", "description", "address"),
            {
                "vessel": "Vessel",
                "tag": "Tag",
                "changed": "Changed Fields",
                "description": "Description",
                "address": "Address",
            },
            {
                "vessel": 110,
                "tag": 160,
                "changed": 140,
                "description": 280,
                "address": 120,
            },
            height=16,
        )
        self._tree.configure(selectmode="browse")

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(
            buttons, text="Edit Row", command=self._edit_row, **button_neutral_kwargs()
        ).pack(side="left")
        ctk.CTkButton(
            buttons, text="Remove Row", command=self._remove_row, **button_neutral_kwargs()
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons, text="Close", command=self._window.destroy, **button_neutral_kwargs()
        ).pack(side="right")

        self._status_var = tk.StringVar()
        ctk.CTkLabel(buttons, textvariable=self._status_var, font=FONT_BODY).pack(
            side="right", padx=(0, 16)
        )
        self._render()

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for entry in self._queue.all_entries():
            name = str(entry.row_data.get("Name", "")).strip().upper()
            description = str(entry.row_data.get("Description", "")).strip().upper()
            address = str(
                entry.row_data.get("IOAddress", entry.row_data.get("Address", ""))
            ).strip().upper()
            changed = ", ".join(changed_field_labels(entry.baseline, entry.row_data))
            self._tree.insert(
                "",
                "end",
                iid=entry.change_id,
                values=(entry.vessel, name, changed, description, address),
            )
        self._status_var.set(f"Pending: {self._queue.count()} row(s)")

    def _selected_change_id(self) -> str | None:
        selection = self._tree.selection()
        return str(selection[0]) if selection else None

    def _edit_row(self) -> None:
        change_id = self._selected_change_id()
        if change_id is None:
            messagebox.showinfo("Selection Required", "Select a queue row to edit.")
            return
        entry = self._queue.get(change_id)
        if entry is None:
            return
        name = simpledialog.askstring(
            "Edit Name", "Name:", initialvalue=entry.row_data.get("Name", "")
        )
        if name is None:
            return
        description = simpledialog.askstring(
            "Edit Description",
            "Description:",
            initialvalue=entry.row_data.get("Description", ""),
        )
        if description is None:
            return
        address = simpledialog.askstring(
            "Edit Address",
            "IO Address:",
            initialvalue=entry.row_data.get(
                "IOAddress", entry.row_data.get("Address", "")
            ),
        )
        if address is None:
            return
        row = dict(entry.row_data)
        row["Name"] = name.strip().upper()
        row["Description"] = description.strip().upper()
        if address.strip():
            row["IOAddress"] = address.strip().upper()
            row["Address"] = address.strip().upper()
        self._queue.update_row(change_id, row)
        self._render()
        if self._on_change is not None:
            self._on_change()

    def _remove_row(self) -> None:
        change_id = self._selected_change_id()
        if change_id is None:
            messagebox.showinfo("Selection Required", "Select a queue row to remove.")
            return
        if not messagebox.askyesno("Remove Row", "Remove this row from the export queue?"):
            return
        self._queue.remove(change_id)
        self._render()
        if self._on_change is not None:
            self._on_change()
