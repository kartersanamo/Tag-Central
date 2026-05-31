"""Shared CustomTkinter dialog helpers."""

from __future__ import annotations

import customtkinter as ctk

from ui.ctk_theme import CORNER_RADIUS, FONT_BODY, FONT_SUBTITLE, FONT_TITLE


class CtkModalDialog(ctk.CTkToplevel):
    """Base modal dialog with standard layout."""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        *,
        width: int = 640,
        height: int = 480,
        resizable: bool = False,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(resizable, resizable)
        self.transient(parent)
        self.grab_set()

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=16, pady=16)

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=16, pady=(0, 16))

    def add_title(self, text: str) -> ctk.CTkLabel:
        label = ctk.CTkLabel(self.body, text=text, font=FONT_TITLE, anchor="w")
        label.pack(anchor="w", pady=(0, 4))
        return label

    def add_subtitle(self, text: str) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            self.body,
            text=text,
            font=FONT_SUBTITLE,
            anchor="w",
            wraplength=580,
            justify="left",
        )
        label.pack(anchor="w", pady=(0, 12))
        return label

    def add_readonly_text(self, content: str, *, height: int = 300) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(self.body, height=height, corner_radius=CORNER_RADIUS)
        box.pack(fill="both", expand=True, pady=(0, 8))
        box.insert("1.0", content)
        box.configure(state="disabled")
        return box

    def add_footer_button(
        self,
        text: str,
        command,
        *,
        side: str = "left",
        **kwargs,
    ) -> ctk.CTkButton:
        button = ctk.CTkButton(self.footer, text=text, command=command, **kwargs)
        button.pack(side=side, padx=(0, 8) if side == "left" else (8, 0))
        return button

    def wait_for_close(self) -> None:
        self.wait_window()
