"""Post-import Cimplicity link statistics."""

from __future__ import annotations

import customtkinter as ctk

from ui.ctk_dialog import CtkModalDialog
from ui.ctk_theme import FONT_TITLE, button_neutral_kwargs


class CimplicityLinkReportDialog:
    """Shows how Cimplicity rows were linked during import."""

    def __init__(
        self, parent: ctk.CTk, lines: list[str], apply_summary: list[str]
    ) -> None:
        self._window = CtkModalDialog(
            parent, "Cimplicity Link Report", width=640, height=520
        )
        ctk.CTkLabel(
            self._window.body,
            text="Cimplicity import link breakdown",
            font=FONT_TITLE,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        body = "\n".join(lines)
        if apply_summary:
            body += "\n\n--- Apply results ---\n" + "\n".join(apply_summary)
        self._window.add_readonly_text(body, height=380)
        self._window.add_footer_button(
            "Close", self._window.destroy, side="right", **button_neutral_kwargs()
        )
