"""Side-by-side Proficy vs Cimplicity field comparison."""

from __future__ import annotations

import customtkinter as ctk

from app_config import SYNC_STATUS_LABELS
from models.tag_record import TagRecord
from services.address_normalizer import normalize_address
from services.cross_program_sync_service import normalize_description
from ui.ctk_theme import FONT_BODY, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview

_DIFF_DARK = "#4a3828"


class TagDiffDialog:
    """Shows canonical, Proficy, and Cimplicity values for one tag."""

    def __init__(self, parent: ctk.CTk, record: TagRecord) -> None:
        self._window = ctk.CTkToplevel(parent)
        self._window.title(f"Tag Diff — {record.tag_name}")
        self._window.geometry("900x360")
        self._window.transient(parent)

        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text="Highlighted rows differ between columns.",
            font=FONT_BODY,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        proficy_name = (record.proficy_name or record.tag_name).strip().upper()
        proficy_desc = str(record.proficy_row_data.get("Description", record.description))
        proficy_addr = normalize_address(
            TagRecord._address_from_row(record.proficy_row_data)
        ) or record.linked_address
        cim_name = (record.cimplicity_pt_id or "").strip().upper()
        cim_desc = (
            normalize_description(record.cimplicity_row_data.get("DESC", ""))
            if record.cimplicity_row_data
            else ""
        )
        cim_addr = (
            normalize_address(record.cimplicity_row_data.get("ADDR", ""))
            if record.cimplicity_row_data
            else ""
        )

        sync_label = SYNC_STATUS_LABELS.get(
            record.sync_status, record.sync_status.replace("_", " ").title()
        )

        rows = [
            ("Tag / Name", record.tag_name, proficy_name, cim_name or "—"),
            ("Description", record.description, proficy_desc, cim_desc or "—"),
            ("Address", record.linked_address or "—", proficy_addr or "—", cim_addr or "—"),
            ("Sync", sync_label, "—", "—"),
        ]

        table_frame = ctk.CTkFrame(body)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        tree, _scroll = create_data_treeview(
            table_frame,
            ("field", "canonical", "proficy", "cimplicity"),
            {
                "field": "Field",
                "canonical": "Canonical",
                "proficy": "Proficy",
                "cimplicity": "Cimplicity",
            },
            {"field": 120, "canonical": 220, "proficy": 220, "cimplicity": 220},
            height=6,
        )
        tree.tag_configure("diff", background=_DIFF_DARK)

        for field_name, canonical, proficy, cimplicity in rows:
            differs = len({canonical, proficy, cimplicity} - {"—"}) > 1
            tags = ("diff",) if differs and field_name != "Sync" else ()
            tree.insert(
                "",
                "end",
                values=(field_name, canonical, proficy, cimplicity),
                tags=tags,
            )

        ctk.CTkButton(
            body, text="Close", command=self._window.destroy, **button_neutral_kwargs()
        ).pack(anchor="e")
