"""Review queue for unmatched Cimplicity import rows."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from services.cimplicity_review_queue import CimplicityReviewQueue, ReviewQueueItem


class CimplicityReviewDialog:
    """Shows and manages Cimplicity-only rows awaiting Proficy linkage."""

    def __init__(
        self,
        parent: tk.Tk,
        review_queue: CimplicityReviewQueue,
        on_create_proficy: Callable[[list[ReviewQueueItem]], None] | None = None,
        on_dismiss: Callable[[list[ReviewQueueItem]], None] | None = None,
    ) -> None:
        self._queue = review_queue
        self._on_create_proficy = on_create_proficy
        self._on_dismiss = on_dismiss
        self._window = tk.Toplevel(parent)
        self._window.title("Cimplicity Review Queue")
        self._window.geometry("1100x600")
        self._window.transient(parent)

        ttk.Label(
            self._window,
            text="Unmatched Cimplicity points. Create a Proficy tag or dismiss when handled.",
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        table_frame = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table_frame.pack(fill="both", expand=True)
        columns = ("vessel", "pt_id", "description", "address")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="extended"
        )
        for column, label, width in (
            ("vessel", "Vessel", 120),
            ("pt_id", "PT_ID", 180),
            ("description", "Description", 360),
            ("address", "Address", 120),
        ):
            self._tree.heading(column, text=label)
            self._tree.column(column, width=width, anchor="w")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=y_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")
        ttk.Button(
            button_bar, text="Create Proficy Tag", command=self._create_proficy
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            button_bar,
            text="Create Proficy Tag For All",
            command=self._create_proficy_all,
        ).pack(side="left", padx=8)
        ttk.Button(button_bar, text="Dismiss Selected", command=self._dismiss).pack(
            side="left", padx=8
        )
        ttk.Button(button_bar, text="Dismiss All", command=self._dismiss_all).pack(
            side="left", padx=8
        )
        ttk.Button(button_bar, text="Close", command=self._window.destroy).pack(side="right")

        self._render()

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, item in enumerate(self._queue.items):
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(item.vessel, item.pt_id, item.description, item.address),
            )

    def _selected_items(self) -> list[ReviewQueueItem]:
        items = self._queue.items
        selected: list[ReviewQueueItem] = []
        for item_id in self._tree.selection():
            selected.append(items[int(item_id)])
        return selected

    def _create_proficy(self) -> None:
        selected = self._selected_items()
        if not selected:
            messagebox.showinfo("Selection Required", "Select at least one queue item.")
            return
        if self._on_create_proficy is None:
            return
        self._on_create_proficy(selected)
        self._render()

    def _create_proficy_all(self) -> None:
        all_items = list(self._queue.items)
        if not all_items:
            messagebox.showinfo("Review Queue Empty", "There are no items in the review queue.")
            return
        if self._on_create_proficy is None:
            return
        confirmed = messagebox.askyesno(
            "Create All Proficy Tags",
            f"Create Proficy tags for all {len(all_items)} review queue item(s)?\n\n"
            "Each new tag will be queued for Proficy export.",
        )
        if not confirmed:
            return
        self._on_create_proficy(all_items)
        self._render()

    def _dismiss(self) -> None:
        selected = self._selected_items()
        if not selected:
            return
        if self._on_dismiss is None:
            return
        self._on_dismiss(selected)
        self._render()

    def _dismiss_all(self) -> None:
        all_items = list(self._queue.items)
        if not all_items:
            return
        if self._on_dismiss is None:
            return
        confirmed = messagebox.askyesno(
            "Dismiss All",
            f"Dismiss all {len(all_items)} review queue item(s) without creating Proficy tags?",
        )
        if not confirmed:
            return
        self._on_dismiss(all_items)
        self._render()
