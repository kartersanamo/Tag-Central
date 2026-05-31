"""Pre-import summary before applying Proficy or Cimplicity data."""

from __future__ import annotations

import customtkinter as ctk

from ui.ctk_dialog import CtkModalDialog
from ui.ctk_theme import FONT_SUBTITLE, button_accent_kwargs, button_neutral_kwargs


class ImportDryRunDialog:
    """Shows import analysis and returns whether user chose Apply."""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        summary_lines: list[str],
    ) -> None:
        self._result = False
        self._dialog = CtkModalDialog(parent, title, width=620, height=480)
        self._window = self._dialog

        ctk.CTkLabel(
            self._dialog.body,
            text="Review the import summary, then apply or cancel.",
            font=FONT_SUBTITLE,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        self._dialog.add_readonly_text("\n".join(summary_lines), height=320)
        self._dialog.add_footer_button(
            "Apply Import", self._apply, **button_accent_kwargs()
        )
        self._dialog.add_footer_button(
            "Cancel", self._cancel, side="right", **button_neutral_kwargs()
        )
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

    def _apply(self) -> None:
        self._result = True
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = False
        self._window.destroy()

    def show(self) -> bool:
        self._window.wait_window()
        return self._result
