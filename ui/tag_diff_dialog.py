"""Side-by-side Proficy vs Cimplicity field comparison."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app_config import SYNC_STATUS_LABELS
from models.tag_record import TagRecord
from services.address_normalizer import normalize_address
from services.cross_program_sync_service import normalize_description


class TagDiffDialog:
    """Shows canonical, Proficy, and Cimplicity values for one tag."""

    def __init__(self, parent: tk.Tk, record: TagRecord) -> None:
        self._window = tk.Toplevel(parent)
        self._window.title(f"Tag Diff — {record.tag_name}")
        self._window.geometry("900x360")
        self._window.transient(parent)

        ttk.Label(
            self._window,
            text="Highlighted rows differ between columns.",
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        proficy_name = (record.proficy_name or record.tag_name).strip().upper()
        proficy_desc = str(record.proficy_row_data.get("Description", record.description))
        proficy_addr = normalize_address(
            TagRecord._address_from_row(record.proficy_row_data)
        ) or record.linked_address
        cim_name = (record.cimplicity_pt_id or "").strip().upper()
        cim_desc = normalize_description(
            record.cimplicity_row_data.get("DESC", "")
        ) if record.cimplicity_row_data else ""
        cim_addr = normalize_address(
            record.cimplicity_row_data.get("ADDR", "")
        ) if record.cimplicity_row_data else ""

        sync_label = SYNC_STATUS_LABELS.get(
            record.sync_status, record.sync_status.replace("_", " ").title()
        )

        rows = [
            ("Tag / Name", record.tag_name, proficy_name, cim_name or "—"),
            ("Description", record.description, proficy_desc, cim_desc or "—"),
            ("Address", record.linked_address or "—", proficy_addr or "—", cim_addr or "—"),
            ("Sync", sync_label, "—", "—"),
        ]

        table = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table.pack(fill="both", expand=True)
        columns = ("field", "canonical", "proficy", "cimplicity")
        tree = ttk.Treeview(table, columns=columns, show="headings", height=6)
        for column, label, width in (
            ("field", "Field", 120),
            ("canonical", "Canonical", 220),
            ("proficy", "Proficy", 220),
            ("cimplicity", "Cimplicity", 220),
        ):
            tree.heading(column, text=label)
            tree.column(column, width=width, anchor="w")
        tree.tag_configure("diff", background="#fff3e0")
        tree.pack(fill="both", expand=True)

        for field_name, canonical, proficy, cimplicity in rows:
            differs = len({canonical, proficy, cimplicity} - {"—"}) > 1
            tags = ("diff",) if differs and field_name != "Sync" else ()
            tree.insert(
                "",
                "end",
                values=(field_name, canonical, proficy, cimplicity),
                tags=tags,
            )

        ttk.Button(self._window, text="Close", command=self._window.destroy).pack(
            pady=(0, 14)
        )
