"""Lightweight startup splash shown before heavy modules load."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from app_identity import APP_NAME, APP_VERSION, icon_png_path
from ui.ctk_theme import BRAND_TEAL, FONT_BODY, FONT_SUBTITLE, FONT_TITLE


class StartupSplash:
    """Borderless splash with logo, title, status text, and indeterminate progress."""

    WIDTH = 420
    HEIGHT = 260

    def __init__(self, master: ctk.CTk) -> None:
        self._master = master
        self._window = ctk.CTkToplevel(master)
        self._window.title(APP_NAME)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._status_var = tk.StringVar(value="Starting…")
        self._icon_image: tk.PhotoImage | None = None
        self._build_ui()
        self._center_on_screen()
        self._window.update_idletasks()
        self._window.update()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self._window)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        png_path = icon_png_path()
        if png_path.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(png_path))
                tk.Label(frame, image=self._icon_image, bg="#2b2b2b").pack(
                    pady=(0, 12)
                )
            except tk.TclError:
                pass

        title = APP_NAME
        if APP_VERSION:
            title = f"{APP_NAME} {APP_VERSION}"
        ctk.CTkLabel(frame, text=title, font=FONT_TITLE).pack()
        ctk.CTkLabel(
            frame,
            text="Opening application…",
            font=FONT_SUBTITLE,
        ).pack(pady=(4, 16))
        ctk.CTkLabel(frame, textvariable=self._status_var, font=FONT_BODY).pack(
            pady=(0, 10)
        )
        progress = ctk.CTkProgressBar(frame, mode="indeterminate", width=320)
        progress.pack(fill="x")
        progress.start()

    def _center_on_screen(self) -> None:
        self._window.update_idletasks()
        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        x = (screen_w - self.WIDTH) // 2
        y = (screen_h - self.HEIGHT) // 2
        self._window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def set_status(self, message: str) -> None:
        self._status_var.set(message)
        self._window.update_idletasks()
        self._window.update()

    def close(self) -> None:
        try:
            if self._window.winfo_exists():
                self._window.destroy()
        except tk.TclError:
            pass
        self._master.update_idletasks()
