"""Pre-import summary before applying Proficy or Cimplicity data."""

from __future__ import annotations

import tkinter as tk

from ui.report_dialog import ReportDialog


class ImportDryRunDialog:
    """Shows import analysis and returns whether user chose Apply."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        summary_lines: list[str],
    ) -> None:
        self._dialog = ReportDialog(
            parent,
            title,
            intro="Review the import summary, then apply or cancel.",
            apply_label="Apply Import",
        )
        self._dialog.set_content("\n".join(summary_lines))

    def show(self) -> bool:
        return self._dialog.show()
