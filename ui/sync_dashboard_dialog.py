"""Cross-program sync status dashboard."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from app_config import SYNC_STATUS_LABELS
from models.tag_record import (
    SYNC_NAME_MISMATCH,
    SYNC_NEEDS_ALIGN,
    SYNC_PROFICY_DRIFT,
    SYNC_PROFICY_ONLY,
    SYNC_SYNCED,
    TagRecord,
)


class SyncDashboardDialog:
    """Summarizes sync health across Proficy and Cimplicity."""

    CATEGORIES = (
        ("synced", "Synced"),
        ("proficy_drift", "Proficy Drift"),
        ("name_mismatch", "Name Mismatch"),
        ("needs_align", "Needs Align"),
        ("proficy_only", "Proficy Only"),
    )

    def __init__(
        self,
        parent: tk.Tk,
        tags: dict[str, TagRecord],
        review_queue_count: int,
        on_align_selected: Callable[[list[str]], None] | None = None,
    ) -> None:
        self._tags = tags
        self._on_align_selected = on_align_selected
        self._window = tk.Toplevel(parent)
        self._window.title("Sync Dashboard")
        self._window.geometry("1200x650")
        self._window.transient(parent)

        summary = ttk.Frame(self._window, padding=14)
        summary.pack(fill="x")
        counts = self._count_by_status()
        summary_text = (
            f"Total tags: {len(tags)} · "
            f"Synced: {counts.get(SYNC_SYNCED, 0)} · "
            f"Proficy drift: {counts.get(SYNC_PROFICY_DRIFT, 0)} · "
            f"Proficy only: {counts.get(SYNC_PROFICY_ONLY, 0)} · "
            f"Cimplicity review queue: {review_queue_count}"
        )
        ttk.Label(summary, text=summary_text, font=("Helvetica", 11, "bold")).pack(
            anchor="w"
        )

        notebook = ttk.Notebook(self._window)
        notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self._trees: dict[str, ttk.Treeview] = {}
        for status_key, label in self.CATEGORIES:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=f"{label} ({counts.get(status_key, 0)})")
            tree = ttk.Treeview(
                frame,
                columns=("tag", "proficy_name", "cimplicity_pt_id", "description", "address"),
                show="headings",
            )
            for column, heading, width in (
                ("tag", "Canonical Tag", 160),
                ("proficy_name", "Proficy Name", 160),
                ("cimplicity_pt_id", "Cimplicity PT_ID", 160),
                ("description", "Description", 280),
                ("address", "Address", 120),
            ):
                tree.heading(column, text=heading)
                tree.column(column, width=width, anchor="w")
            tree.pack(fill="both", expand=True, side="left")
            scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side="left", fill="y")
            self._trees[status_key] = tree
            self._fill_category(tree, status_key)

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")
        if on_align_selected is not None:
            ttk.Button(
                button_bar,
                text="Align Selected (Drift Tab)",
                command=self._align_from_drift_tab,
            ).pack(side="left")
        ttk.Button(button_bar, text="Close", command=self._window.destroy).pack(side="right")

    def _count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self._tags.values():
            counts[record.sync_status] = counts.get(record.sync_status, 0) + 1
        return counts

    def _fill_category(self, tree: ttk.Treeview, status_key: str) -> None:
        for tag_name, record in sorted(self._tags.items()):
            if record.sync_status != status_key:
                continue
            tree.insert(
                "",
                "end",
                iid=tag_name,
                values=(
                    tag_name,
                    record.proficy_name or "",
                    record.cimplicity_pt_id or "",
                    record.description,
                    record.linked_address,
                ),
            )

    def _align_from_drift_tab(self) -> None:
        if self._on_align_selected is None:
            return
        tree = self._trees.get(SYNC_PROFICY_DRIFT)
        if tree is None:
            return
        selected = [str(item) for item in tree.selection()]
        if not selected:
            return
        self._on_align_selected(selected)
