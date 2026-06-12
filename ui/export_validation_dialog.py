"""Shows Proficy export file validation results."""

from __future__ import annotations

import tkinter as tk

from models.export_validation_result import ExportValidationResult
from ui.report_dialog import ReportDialog


class ExportValidationDialog:
    """Summarizes per-file export validation."""

    def __init__(self, parent: tk.Tk, results: list[ExportValidationResult]) -> None:
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

        self._dialog = ReportDialog(parent, "Export Validation")
        self._dialog.set_content("\n".join(lines) if lines else "No files validated.")
        self._dialog.show_readonly()
