"""Review queue for unmatched Cimplicity import rows."""

from __future__ import annotations

from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from services.cimplicity_review_queue import CimplicityReviewQueue, ReviewQueueItem
from ui.ctk_theme import FONT_BODY, button_accent_kwargs, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview


class CimplicityReviewDialog:
    """Shows and manages Cimplicity-only rows awaiting Proficy linkage."""

    def __init__(
        self,
        parent: ctk.CTk,
        review_queue: CimplicityReviewQueue,
        on_create_proficy: Callable[[list[ReviewQueueItem]], None] | None = None,
        on_dismiss: Callable[[list[ReviewQueueItem]], None] | None = None,
    ) -> None:
        self._queue = review_queue
        self._on_create_proficy = on_create_proficy
        self._on_dismiss = on_dismiss
        self._window = ctk.CTkToplevel(parent)
        self._window.title("Cimplicity Review Queue")
        self._window.geometry("1100x600")
        self._window.transient(parent)

        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text="Unmatched Cimplicity points. Create a Proficy tag or dismiss when handled.",
            font=FONT_BODY,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        table_frame = ctk.CTkFrame(body)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        self._tree, _scroll = create_data_treeview(
            table_frame,
            ("vessel", "pt_id", "description", "address"),
            {
                "vessel": "Vessel",
                "pt_id": "PT_ID",
                "description": "Description",
                "address": "Address",
            },
            {"vessel": 120, "pt_id": 180, "description": 360, "address": 120},
            height=16,
        )
        self._tree.configure(selectmode="extended")

        button_bar = ctk.CTkFrame(body, fg_color="transparent")
        button_bar.pack(fill="x")
        ctk.CTkButton(
            button_bar,
            text="Create Proficy Tag",
            command=self._create_proficy,
            **button_accent_kwargs(),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            button_bar,
            text="Create Proficy Tag For All",
            command=self._create_proficy_all,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            button_bar, text="Dismiss Selected", command=self._dismiss, **button_neutral_kwargs()
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            button_bar, text="Dismiss All", command=self._dismiss_all, **button_neutral_kwargs()
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            button_bar, text="Close", command=self._window.destroy, **button_neutral_kwargs()
        ).pack(side="right")

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
