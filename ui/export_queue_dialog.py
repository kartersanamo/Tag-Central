"""Review and edit pending Proficy export queue entries."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

from services.export_queue_service import ExportQueueService, changed_field_labels


class ExportQueueDialog:
    """Lists pending export rows with per-row edit and remove."""

    def __init__(
        self,
        parent: tk.Tk,
        queue: ExportQueueService,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._queue = queue
        self._on_change = on_change
        self._window = tk.Toplevel(parent)
        self._window.title("Export Queue")
        self._window.geometry("1100x600")
        self._window.transient(parent)

        ttk.Label(
            self._window,
            text="Review pending Proficy export rows before running Export Changes.",
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        table_frame = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table_frame.pack(fill="both", expand=True)
        columns = ("vessel", "tag", "changed", "description", "address")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        for column, label, width in (
            ("vessel", "Vessel", 110),
            ("tag", "Tag", 160),
            ("changed", "Changed Fields", 140),
            ("description", "Description", 280),
            ("address", "Address", 120),
        ):
            self._tree.heading(column, text=label)
            self._tree.column(column, width=width, anchor="w")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=y_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        buttons = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Edit Row", command=self._edit_row).pack(side="left")
        ttk.Button(buttons, text="Remove Row", command=self._remove_row).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="Close", command=self._window.destroy).pack(side="right")

        self._status_var = tk.StringVar()
        ttk.Label(buttons, textvariable=self._status_var).pack(side="right", padx=(0, 16))
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
