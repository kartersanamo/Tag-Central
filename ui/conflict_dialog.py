"""UI dialog for resolving all import conflicts in one screen."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ui.ctk_theme import BRAND_TEAL, FONT_BODY, button_accent_kwargs, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview


class ConflictDialog:
    """Collects bulk decisions for all detected conflicts."""

    def __init__(self, parent: ctk.CTk) -> None:
        self._result: list[dict[str, str]] | None = None
        self._decision_var = tk.StringVar(value="pending")
        self._window = ctk.CTkToplevel(parent)
        self._window.title("Bulk Conflict Resolver")
        self._window.geometry("1300x720")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._header_var = tk.StringVar(value="")
        self._selected_action_var = tk.StringVar(value="skip")
        self._status_var = tk.StringVar(value="")
        self._conflicts: list[dict[str, str]] = []

        self._build_ui()

    def resolve_conflicts(
        self, vessel: str, conflicts: list[dict[str, str]]
    ) -> list[dict[str, str]] | None:
        self._result = None
        self._decision_var.set("pending")
        self._conflicts = [dict(conflict) for conflict in conflicts]
        self._header_var.set(
            f"Vessel '{vessel}' has {len(conflicts)} conflicts. Resolve all rows below."
        )
        self._render_rows()
        self._refresh_status()

        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._window.wait_variable(self._decision_var)
        return self._result

    def close(self) -> None:
        if self._window.winfo_exists():
            self._window.destroy()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self._window, textvariable=self._header_var, font=FONT_BODY, anchor="w", justify="left"
        ).pack(fill="x", padx=16, pady=(14, 10))
        ctk.CTkLabel(
            self._window,
            textvariable=self._status_var,
            text_color=BRAND_TEAL,
            font=(FONT_BODY[0], FONT_BODY[1], "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        table_frame = ctk.CTkFrame(self._window)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._tree, _scroll = create_data_treeview(
            table_frame,
            ("action", "imported_tag", "imported_desc", "existing_tag", "existing_desc"),
            {
                "action": "Action",
                "imported_tag": "Imported Tag",
                "imported_desc": "Imported Description",
                "existing_tag": "Existing Tag",
                "existing_desc": "Existing Description",
            },
            {
                "action": 150,
                "imported_tag": 180,
                "imported_desc": 310,
                "existing_tag": 180,
                "existing_desc": 310,
            },
            height=18,
        )
        self._tree.configure(selectmode="extended")

        button_bar = ctk.CTkFrame(self._window, fg_color="transparent")
        button_bar.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(button_bar, text="Set selected rows to:", font=FONT_BODY).pack(side="left")
        ctk.CTkComboBox(
            button_bar,
            variable=self._selected_action_var,
            state="readonly",
            values=("skip", "use_imported", "use_existing", "keep_both"),
            width=160,
        ).pack(side="left", padx=(8, 8))
        ctk.CTkButton(
            button_bar,
            text="Apply To Selected",
            command=self._apply_selected,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=(0, 16))
        ctk.CTkButton(
            button_bar,
            text="Use Imported For All",
            command=lambda: self._apply_all("use_imported"),
            **button_neutral_kwargs(),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            button_bar,
            text="Use Existing For All",
            command=lambda: self._apply_all("use_existing"),
            **button_neutral_kwargs(),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            button_bar,
            text="Keep Both For All",
            command=lambda: self._apply_all("keep_both"),
            **button_neutral_kwargs(),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            button_bar,
            text="Skip All",
            command=lambda: self._apply_all("skip"),
            **button_neutral_kwargs(),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            button_bar, text="Cancel Import", command=self._on_window_close, **button_neutral_kwargs()
        ).pack(side="right")
        ctk.CTkButton(
            button_bar, text="Apply Decisions", command=self._submit, **button_accent_kwargs()
        ).pack(side="right", padx=(0, 8))

    def _render_rows(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, conflict in enumerate(self._conflicts):
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    conflict.get("action", "skip"),
                    conflict["imported_tag"],
                    conflict["imported_description"],
                    conflict["existing_tag"],
                    conflict["existing_description"],
                ),
            )

    def _apply_selected(self) -> None:
        action = self._selected_action_var.get()
        for item in self._tree.selection():
            index = int(item)
            self._conflicts[index]["action"] = action
        self._render_rows()
        self._refresh_status()

    def _apply_all(self, action: str) -> None:
        for conflict in self._conflicts:
            conflict["action"] = action
        self._render_rows()
        self._refresh_status()

    def _submit(self) -> None:
        self._result = self._conflicts
        self._decision_var.set("done")

    def _refresh_status(self) -> None:
        counts = {
            "skip": 0,
            "use_imported": 0,
            "use_existing": 0,
            "keep_both": 0,
        }
        for conflict in self._conflicts:
            counts[conflict.get("action", "skip")] += 1
        self._status_var.set(
            "Decision breakdown - "
            f"Skip: {counts['skip']} | "
            f"Use Imported: {counts['use_imported']} | "
            f"Use Existing: {counts['use_existing']} | "
            f"Keep Both: {counts['keep_both']}"
        )

    def _on_window_close(self) -> None:
        self._result = None
        self._decision_var.set("done")
