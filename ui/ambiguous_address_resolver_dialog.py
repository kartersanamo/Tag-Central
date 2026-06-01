"""Dedicated resolver for Cimplicity rows with ambiguous address matches."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class AmbiguousAddressResolverDialog:
    """Collects decisions for ambiguous address collisions."""

    ACTIONS = (
        "align_selected",
        "merge_then_align",
        "link_only_selected",
        "flag_manual_cimplicity",
        "skip",
    )

    ACTION_LABELS = {
        "align_selected": "Align Selected Tag",
        "merge_then_align": "Merge Duplicates Then Align",
        "link_only_selected": "Link Only (Needs Align)",
        "flag_manual_cimplicity": "Flag Manual Cimplicity",
        "skip": "Skip",
    }

    def __init__(self, parent: tk.Tk) -> None:
        self._result: list[dict[str, str]] | None = None
        self._decision_var = tk.StringVar(value="pending")
        self._window = tk.Toplevel(parent)
        self._window.title("Ambiguous Address Resolver")
        self._window.geometry("1560x780")
        self._window.transient(parent)
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._header_var = tk.StringVar(value="")
        self._status_var = tk.StringVar(value="")
        self._selected_action_var = tk.StringVar(
            value=self.ACTION_LABELS["align_selected"]
        )
        self._selected_tag_var = tk.StringVar(value="")
        self._rows: list[dict[str, str]] = []
        self._build_ui()

    def resolve_rows(
        self, vessel: str, rows: list[dict[str, str]]
    ) -> list[dict[str, str]] | None:
        self._result = None
        self._decision_var.set("pending")
        self._rows = [dict(row) for row in rows]
        for row in self._rows:
            candidates = self._parse_candidates(str(row.get("candidate_tags", "")))
            row.setdefault("action", "align_selected")
            row.setdefault("selected_tag", candidates[0] if candidates else "")
        self._header_var.set(
            f"Vessel '{vessel}': {len(rows)} rows matched multiple tags by address.\n"
            "Pick a survivor tag for each row, optionally merge duplicates, then apply."
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
        wrapper = ttk.Frame(self._window, padding=14)
        wrapper.pack(fill="both", expand=True)

        ttk.Label(
            wrapper,
            textvariable=self._header_var,
            justify="left",
            font=("Helvetica", 12, "bold"),
        ).pack(fill="x", pady=(0, 6))
        ttk.Label(
            wrapper,
            text=(
                "Recommendation: use 'Merge Duplicates Then Align' when candidate tags are "
                "duplicate aliases for the same IO address."
            ),
            foreground="#0f4c81",
        ).pack(fill="x", pady=(0, 6))
        ttk.Label(
            wrapper,
            textvariable=self._status_var,
            foreground="#8a5b00",
            font=("Helvetica", 11, "bold"),
        ).pack(fill="x", pady=(0, 10))

        table_frame = ttk.Frame(wrapper)
        table_frame.pack(fill="both", expand=True)
        columns = (
            "action",
            "pt_id",
            "cim_desc",
            "address",
            "selected_tag",
            "candidate_tags",
        )
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
        )
        headings = {
            "action": "Resolution",
            "pt_id": "Cimplicity PT_ID",
            "cim_desc": "Cimplicity Description",
            "address": "Address",
            "selected_tag": "Selected Survivor Tag",
            "candidate_tags": "Candidate Tags",
        }
        widths = {
            "action": 220,
            "pt_id": 210,
            "cim_desc": 300,
            "address": 130,
            "selected_tag": 220,
            "candidate_tags": 420,
        }
        for col in columns:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, width=widths[col], anchor="w")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=y_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="left", fill="y")

        controls = ttk.Frame(wrapper, padding=(0, 10, 0, 0))
        controls.pack(fill="x")
        ttk.Label(controls, text="Set selected rows to action:").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self._selected_action_var,
            state="readonly",
            values=[self.ACTION_LABELS[action] for action in self.ACTIONS],
            width=32,
        ).pack(side="left", padx=(8, 10))
        ttk.Label(controls, text="with survivor tag:").pack(side="left")
        ttk.Entry(controls, textvariable=self._selected_tag_var, width=26).pack(
            side="left", padx=(8, 10)
        )
        ttk.Button(controls, text="Apply To Selected", command=self._apply_selected).pack(
            side="left", padx=(0, 16)
        )
        ttk.Button(
            controls,
            text="Merge + Align All",
            command=lambda: self._apply_all("merge_then_align"),
        ).pack(side="left", padx=4)
        ttk.Button(
            controls, text="Skip All", command=lambda: self._apply_all("skip")
        ).pack(side="left", padx=4)

        actions = ttk.Frame(wrapper, padding=(0, 10, 0, 0))
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel Import", command=self._on_window_close).pack(
            side="right"
        )
        ttk.Button(actions, text="Apply Decisions", command=self._submit).pack(
            side="right", padx=(0, 8)
        )

        self._tree.bind("<<TreeviewSelect>>", self._sync_editor_with_selection)

    def _render_rows(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, row in enumerate(self._rows):
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    self.ACTION_LABELS.get(row.get("action", "skip"), "Skip"),
                    row.get("pt_id", ""),
                    row.get("cimplicity_description", ""),
                    row.get("address", ""),
                    row.get("selected_tag", ""),
                    row.get("candidate_tags", ""),
                ),
            )

    def _apply_selected(self) -> None:
        label = self._selected_action_var.get().strip()
        action = self._action_from_label(label)
        selected_survivor = self._selected_tag_var.get().strip().upper()
        for item in self._tree.selection():
            idx = int(item)
            row = self._rows[idx]
            row["action"] = action
            candidates = self._parse_candidates(str(row.get("candidate_tags", "")))
            if selected_survivor and selected_survivor in candidates:
                row["selected_tag"] = selected_survivor
            elif not row.get("selected_tag") and candidates:
                row["selected_tag"] = candidates[0]
        self._render_rows()
        self._refresh_status()

    def _apply_all(self, action: str) -> None:
        for row in self._rows:
            row["action"] = action
            if not row.get("selected_tag"):
                candidates = self._parse_candidates(str(row.get("candidate_tags", "")))
                row["selected_tag"] = candidates[0] if candidates else ""
        self._render_rows()
        self._refresh_status()

    def _submit(self) -> None:
        self._result = self._rows
        self._decision_var.set("done")

    def _refresh_status(self) -> None:
        counts = {action: 0 for action in self.ACTIONS}
        for row in self._rows:
            action = row.get("action", "skip")
            counts[action] = counts.get(action, 0) + 1
        parts = [
            f"{self.ACTION_LABELS[action]}: {counts[action]}" for action in self.ACTIONS
        ]
        self._status_var.set(" | ".join(parts))

    def _sync_editor_with_selection(self, _: object) -> None:
        selected = self._tree.selection()
        if len(selected) != 1:
            return
        row = self._rows[int(selected[0])]
        self._selected_tag_var.set(str(row.get("selected_tag", "")))
        action = str(row.get("action", "align_selected"))
        self._selected_action_var.set(self.ACTION_LABELS.get(action, "Skip"))

    @staticmethod
    def _parse_candidates(raw: str) -> list[str]:
        return [item.strip().upper() for item in raw.split(",") if item.strip()]

    def _action_from_label(self, label: str) -> str:
        for action, action_label in self.ACTION_LABELS.items():
            if action_label == label:
                return action
        return "skip"

    def _on_window_close(self) -> None:
        self._result = None
        self._decision_var.set("done")

