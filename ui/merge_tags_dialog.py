"""Pick survivor tag when merging two records."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ui.ctk_theme import FONT_BODY, button_accent_kwargs, button_neutral_kwargs


class MergeTagsDialog:
    """Returns the canonical tag name to keep after merge."""

    def __init__(self, parent: ctk.CTk, tag_a: str, tag_b: str) -> None:
        self._result: str | None = None
        self._window = ctk.CTkToplevel(parent)
        self._window.title("Merge Tags")
        self._window.geometry("480x240")
        self._window.transient(parent)
        self._window.grab_set()

        self._choice = tk.StringVar(value=tag_a)
        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text="Select which tag survives. The other will be removed.",
            font=FONT_BODY,
            wraplength=440,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkRadioButton(body, text=tag_a, variable=self._choice, value=tag_a).pack(
            anchor="w", padx=6
        )
        ctk.CTkRadioButton(body, text=tag_b, variable=self._choice, value=tag_b).pack(
            anchor="w", padx=6, pady=(4, 0)
        )

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(16, 0))
        ctk.CTkButton(buttons, text="Merge", command=self._confirm, **button_accent_kwargs()).pack(
            side="left"
        )
        ctk.CTkButton(
            buttons, text="Cancel", command=self._cancel, **button_neutral_kwargs()
        ).pack(side="right")

    def _confirm(self) -> None:
        self._result = self._choice.get().strip().upper()
        if not self._result:
            messagebox.showwarning("Invalid", "Select a survivor tag.")
            return
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()

    def show(self) -> str | None:
        self._window.wait_window()
        return self._result
