"""Dialog for checking off manual Cimplicity updates."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from services.cimplicity_manual_tasks import CimplicityManualTasks
from ui.ctk_theme import FONT_BODY, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview


class CimplicityManualTasksDialog:
    """Shows all manual Cimplicity tasks with per-item checkboxes."""

    def __init__(
        self,
        parent: ctk.CTk,
        tasks: CimplicityManualTasks,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._tasks = tasks
        self._on_change = on_change
        self._window = ctk.CTkToplevel(parent)
        self._window.title("Cimplicity Manual Tasks")
        self._window.geometry("1250x650")
        self._window.transient(parent)

        self._select_all_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="")

        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text=(
                "Manually update these changes in Cimplicity, then check them off. "
                "Checked tasks are only removed when you click Clear Checked."
            ),
            font=FONT_BODY,
            wraplength=1180,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 8))
        ctk.CTkCheckBox(
            controls,
            text="Select all",
            variable=self._select_all_var,
            command=self._select_all,
            font=FONT_BODY,
        ).pack(side="left")
        ctk.CTkLabel(controls, textvariable=self._status_var, font=FONT_BODY).pack(side="right")

        table_frame = ctk.CTkFrame(body)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        columns = ("done", "vessel", "tag", "field", "old", "new", "reason", "created")
        headings = {
            "done": "Done",
            "vessel": "Vessel",
            "tag": "Tag",
            "field": "Field",
            "old": "Old Value",
            "new": "New Value",
            "reason": "Reason",
            "created": "Created",
        }
        widths = {
            "done": 70,
            "vessel": 110,
            "tag": 170,
            "field": 110,
            "old": 190,
            "new": 190,
            "reason": 260,
            "created": 190,
        }
        self._tree, _scroll = create_data_treeview(
            table_frame, columns, headings, widths, height=16
        )
        self._tree.configure(selectmode="extended")

        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<space>", lambda *_: self._toggle_selected())

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(
            buttons, text="Toggle Selected", command=self._toggle_selected, **button_neutral_kwargs()
        ).pack(side="left")
        ctk.CTkButton(
            buttons, text="Clear Checked", command=self._clear_checked, **button_neutral_kwargs()
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons, text="Close", command=self._window.destroy, **button_neutral_kwargs()
        ).pack(side="right")

        self._render()

    def show_modal(self) -> None:
        self._window.grab_set()
        self._window.wait_window()

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for item in self._tasks.items:
            marker = "☑" if item.done else "☐"
            self._tree.insert(
                "",
                "end",
                iid=item.task_id,
                values=(
                    marker,
                    item.vessel,
                    item.tag_name,
                    item.field.upper(),
                    item.old_value,
                    item.new_value,
                    item.reason,
                    item.created_at,
                ),
            )
        pending = self._tasks.pending_count()
        total = len(self._tasks.items)
        self._status_var.set(f"Pending: {pending} / Total: {total}")
        self._select_all_var.set(total > 0 and pending == 0)

    def _select_all(self) -> None:
        self._tasks.set_all_done(self._select_all_var.get())
        self._render()
        if self._on_change is not None:
            self._on_change()

    def _toggle_selected(self) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        current = self._tasks.items
        task_map = {item.task_id: item for item in current}
        for task_id in selected:
            task = task_map.get(str(task_id))
            if task is None:
                continue
            self._tasks.set_done(task.task_id, not task.done)
        self._render()
        if self._on_change is not None:
            self._on_change()

    def _clear_checked(self) -> None:
        cleared = self._tasks.clear_done()
        if cleared == 0:
            messagebox.showinfo("No Checked Tasks", "No checked tasks to clear.")
            return
        self._render()
        if self._on_change is not None:
            self._on_change()
        messagebox.showinfo("Cleared", f"Cleared {cleared} checked task(s).")

    def _on_double_click(self, event: tk.Event) -> None:
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        self._tree.selection_set(row_id)
        self._toggle_selected()
