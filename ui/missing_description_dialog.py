"""Dialog for reviewing rows missing descriptions."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ui.ctk_theme import (
    FONT_BODY,
    FONT_TITLE,
    button_accent_kwargs,
    button_neutral_kwargs,
)
from ui.ctk_tree import create_data_treeview


class MissingDescriptionDialog:
    """Allows user review/edit for generated descriptions before import."""

    def __init__(
        self,
        parent: ctk.CTk,
        candidates: list[dict[str, object]],
        *,
        title: str = "Review Missing Descriptions",
    ) -> None:
        self._candidates = candidates
        self._result: dict[int, str] | None = None
        self._window = ctk.CTkToplevel(parent)
        self._window.title(title)
        self._window.geometry("980x620")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        self._description_var = tk.StringVar(value="")
        self._build_ui()

    def show(self) -> dict[int, str] | None:
        self._window.wait_window()
        return self._result

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self._window, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(
            header,
            text="Some rows are missing descriptions.",
            font=FONT_TITLE,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Review suggested descriptions below, edit as needed, then continue.",
            font=FONT_BODY,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        table_frame = ctk.CTkFrame(self._window)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._tree, _scroll = create_data_treeview(
            table_frame,
            ("tag", "suggested", "final"),
            {
                "tag": "Tag",
                "suggested": "Suggested Description",
                "final": "Final Description",
            },
            {"tag": 250, "suggested": 320, "final": 340},
            height=14,
        )
        self._tree.configure(selectmode="browse")

        for candidate in self._candidates:
            row_index = int(candidate["row_index"])
            tag = str(candidate["tag"])
            suggested = str(candidate["suggested"])
            self._tree.insert(
                "",
                "end",
                iid=str(row_index),
                values=(tag, suggested, suggested),
            )

        editor = ctk.CTkFrame(self._window, fg_color="transparent")
        editor.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(editor, text="Edit selected final description:", font=FONT_BODY).pack(
            side="left"
        )
        ctk.CTkEntry(editor, textvariable=self._description_var, width=520).pack(
            side="left", padx=(10, 8), fill="x", expand=True
        )
        ctk.CTkButton(
            editor, text="Apply", command=self._apply_selected_edit, **button_accent_kwargs()
        ).pack(side="left")

        actions = ctk.CTkFrame(self._window, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(
            actions, text="Cancel Import", command=self._cancel, **button_neutral_kwargs()
        ).pack(side="right")
        ctk.CTkButton(
            actions,
            text="Continue Import",
            command=self._continue_import,
            **button_accent_kwargs(),
        ).pack(side="right", padx=(0, 8))

        self._tree.bind("<<TreeviewSelect>>", self._sync_editor_with_selection)
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._sync_editor_with_selection(None)

    def _sync_editor_with_selection(self, _: object) -> None:
        selection = self._tree.selection()
        if not selection:
            self._description_var.set("")
            return
        values = self._tree.item(selection[0], "values")
        self._description_var.set(str(values[2]))

    def _apply_selected_edit(self) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self._tree.item(item_id, "values")
        self._tree.item(
            item_id, values=(values[0], values[1], self._description_var.get().strip())
        )

    def _continue_import(self) -> None:
        result: dict[int, str] = {}
        for item_id in self._tree.get_children():
            values = self._tree.item(item_id, "values")
            result[int(item_id)] = str(values[2]).strip().upper()
        self._result = result
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()
