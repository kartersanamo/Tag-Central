"""UI dialog for resolving all import conflicts in one screen."""

from __future__ import annotations

import tkinter as tk

from ui.bulk_resolver_dialog import BulkResolverDialog


class ConflictDialog:
    """Collects bulk decisions for all detected conflicts."""

    _ACTIONS = ("skip", "use_imported", "use_existing", "keep_both")

    def __init__(self, parent: tk.Tk) -> None:
        self._resolver = BulkResolverDialog(
            parent,
            "Bulk Conflict Resolver",
            columns=(
                "action",
                "imported_tag",
                "imported_desc",
                "existing_tag",
                "existing_desc",
            ),
            headings={
                "action": "Action",
                "imported_tag": "Imported Tag",
                "imported_desc": "Imported Description",
                "existing_tag": "Existing Tag",
                "existing_desc": "Existing Description",
            },
            widths={
                "action": 150,
                "imported_tag": 180,
                "imported_desc": 310,
                "existing_tag": 180,
                "existing_desc": 310,
            },
            actions=self._ACTIONS,
        )
        self._resolver.configure_row_mapper(
            lambda row: (
                row.get("action", "skip"),
                row["imported_tag"],
                row["imported_description"],
                row["existing_tag"],
                row["existing_description"],
            )
        )
        for label, action in (
            ("Use Imported For All", "use_imported"),
            ("Use Existing For All", "use_existing"),
            ("Keep Both For All", "keep_both"),
            ("Skip All", "skip"),
        ):
            self._resolver.add_bulk_button(label, action)
        self._resolver.set_status_formatter(self._format_status)

    def resolve_conflicts(
        self, vessel: str, conflicts: list[dict[str, str]]
    ) -> list[dict[str, str]] | None:
        return self._resolver.resolve(
            f"Vessel '{vessel}' has {len(conflicts)} conflicts. Resolve all rows below.",
            conflicts,
        )

    def close(self) -> None:
        self._resolver.close()

    @staticmethod
    def _format_status(rows: list[dict[str, str]]) -> str:
        counts = {action: 0 for action in ConflictDialog._ACTIONS}
        for row in rows:
            counts[row.get("action", "skip")] += 1
        return (
            "Decision breakdown - "
            f"Skip: {counts['skip']} | "
            f"Use Imported: {counts['use_imported']} | "
            f"Use Existing: {counts['use_existing']} | "
            f"Keep Both: {counts['keep_both']}"
        )
