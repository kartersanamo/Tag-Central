"""Shows Proficy export file validation results."""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

from services.export_validation_service import ExportValidationResult


class ExportValidationDialog:
    """Summarizes per-file export validation."""

    def __init__(self, parent: tk.Tk, results: list[ExportValidationResult]) -> None:
        self._window = tk.Toplevel(parent)
        self._window.title("Export Validation")
        self._window.geometry("640x480")
        self._window.transient(parent)

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

        text = scrolledtext.ScrolledText(self._window, height=22, wrap="word")
        text.pack(fill="both", expand=True, padx=14, pady=14)
        text.insert("1.0", "\n".join(lines) if lines else "No files validated.")
        text.configure(state="disabled")

        ttk.Button(self._window, text="Close", command=self._window.destroy).pack(
            pady=(0, 14)
        )
