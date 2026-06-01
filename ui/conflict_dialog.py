"""UI dialog for resolving all import conflicts in one screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ConflictDialog:
    """Collects bulk decisions for all detected conflicts."""

    def __init__(self, parent: tk.Tk) -> None:
        self._result: list[dict[str, str]] | None = None
        self._decision_var = tk.StringVar(value="pending")
        self._window = tk.Toplevel(parent)
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
        """Shows all conflicts and collects user decisions."""
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
        """Destroys the dialog window after the import session."""
        if self._window.winfo_exists():
            self._window.destroy()

    def _build_ui(self) -> None:
        ttk.Label(self._window, textvariable=self._header_var, justify="left").pack(
            fill="x", padx=16, pady=(14, 10)
        )
        ttk.Label(
            self._window,
            textvariable=self._status_var,
            foreground="#0f4c81",
            font=("Helvetica", 11, "bold"),
        ).pack(fill="x", padx=16, pady=(0, 8))

        table_frame = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        table_frame.pack(fill="both", expand=True)
        self._tree = ttk.Treeview(
            table_frame,
            columns=("action", "imported_tag", "imported_desc", "existing_tag", "existing_desc"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("action", text="Action")
        self._tree.heading("imported_tag", text="Imported Tag")
        self._tree.heading("imported_desc", text="Imported Description")
        self._tree.heading("existing_tag", text="Existing Tag")
        self._tree.heading("existing_desc", text="Existing Description")
        self._tree.column("action", width=150, anchor="w")
        self._tree.column("imported_tag", width=180, anchor="w")
        self._tree.column("imported_desc", width=310, anchor="w")
        self._tree.column("existing_tag", width=180, anchor="w")
        self._tree.column("existing_desc", width=310, anchor="w")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=y_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        button_bar = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        button_bar.pack(fill="x")

        ttk.Label(button_bar, text="Set selected rows to:").pack(side="left")
        action_box = ttk.Combobox(
            button_bar,
            textvariable=self._selected_action_var,
            state="readonly",
            values=("skip", "use_imported", "use_existing", "keep_both"),
            width=18,
        )
        action_box.pack(side="left", padx=(8, 8))
        ttk.Button(button_bar, text="Apply To Selected", command=self._apply_selected).pack(
            side="left", padx=(0, 16)
        )
        ttk.Button(button_bar, text="Use Imported For All", command=lambda: self._apply_all("use_imported")).pack(
            side="left", padx=4
        )
        ttk.Button(button_bar, text="Use Existing For All", command=lambda: self._apply_all("use_existing")).pack(
            side="left", padx=4
        )
        ttk.Button(button_bar, text="Keep Both For All", command=lambda: self._apply_all("keep_both")).pack(
            side="left", padx=4
        )
        ttk.Button(button_bar, text="Skip All", command=lambda: self._apply_all("skip")).pack(
            side="left", padx=4
        )

        ttk.Button(button_bar, text="Cancel Import", command=self._on_window_close).pack(
            side="right"
        )
        ttk.Button(button_bar, text="Apply Decisions", command=self._submit).pack(
            side="right", padx=(0, 8)
        )

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
