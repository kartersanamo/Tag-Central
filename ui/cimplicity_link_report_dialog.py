"""Post-import Cimplicity link statistics."""

from __future__ import annotations

import tkinter as tk

from ui.report_dialog import ReportDialog


class CimplicityLinkReportDialog:
    """Shows how Cimplicity rows were linked during import."""

    def __init__(
        self, parent: tk.Tk, lines: list[str], apply_summary: list[str]
    ) -> None:
        body = "\n".join(lines)
        if apply_summary:
            body += "\n\n--- Apply results ---\n" + "\n".join(apply_summary)
        self._dialog = ReportDialog(
            parent,
            "Cimplicity Link Report",
            intro="Cimplicity import link breakdown",
        )
        self._dialog.set_content(body)
