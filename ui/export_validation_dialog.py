"""Shows Proficy export file validation results."""

from __future__ import annotations

import customtkinter as ctk

from services.export_validation_service import ExportValidationResult
from ui.ctk_dialog import CtkModalDialog
from ui.ctk_theme import button_neutral_kwargs


class ExportValidationDialog:
    """Summarizes per-file export validation."""

    def __init__(self, parent: ctk.CTk, results: list[ExportValidationResult]) -> None:
        self._window = CtkModalDialog(parent, "Export Validation", width=640, height=480)
        lines: list[str] = []
        for result in results:
            status = "OK" if result.ok else "ISSUES"
            lines.append(f"[{status}] {result.path.name}")
            lines.append(
                f"  Expected: {result.expected_count}  Found: {result.found_count}"
            )
            if result.missing:
                lines.append(f"  Missing tags: {', '.join(result.missing[:20])}")
                if len(result.missing) > 20:
                    lines.append(f"    ... and {len(result.missing) - 20} more")
            if result.field_mismatches:
                lines.append(
                    f"  Field mismatches: {', '.join(result.field_mismatches[:20])}"
                )
            lines.append("")

        self._window.add_readonly_text(
            "\n".join(lines) if lines else "No files validated.",
            height=360,
        )
        self._window.add_footer_button(
            "Close", self._window.destroy, side="right", **button_neutral_kwargs()
        )
        self._window.grab_set()
        self._window.wait_window()
