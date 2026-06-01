"""Lightweight startup splash shown before heavy modules load."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app_identity import APP_NAME, APP_VERSION, icon_png_path


class StartupSplash:
    """Borderless splash with logo, title, status text, and indeterminate progress."""

    WIDTH = 420
    HEIGHT = 260

    def __init__(self, master: tk.Tk) -> None:
        self._master = master
        self._window = tk.Toplevel(master)
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
        frame = ttk.Frame(self._window, padding=24)
        frame.pack(fill="both", expand=True)

        png_path = icon_png_path()
        if png_path.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(png_path))
                ttk.Label(frame, image=self._icon_image).pack(pady=(0, 12))
            except tk.TclError:
                pass

        title = APP_NAME
        if APP_VERSION:
            title = f"{APP_NAME} {APP_VERSION}"
        ttk.Label(frame, text=title, font=("Helvetica", 18, "bold")).pack()
        ttk.Label(
            frame,
            text="Opening application…",
            font=("Helvetica", 11),
        ).pack(pady=(4, 16))
        ttk.Label(frame, textvariable=self._status_var, font=("Helvetica", 10)).pack(
            pady=(0, 10)
        )
        progress = ttk.Progressbar(frame, mode="indeterminate", length=320)
        progress.pack(fill="x")
        progress.start(10)

    def _center_on_screen(self) -> None:
        self._window.update_idletasks()
        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        x = (screen_w - self.WIDTH) // 2
        y = (screen_h - self.HEIGHT) // 2
        self._window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def set_status(self, message: str) -> None:
        """Updates status line and flushes pending UI events."""
        self._status_var.set(message)
        self._window.update_idletasks()
        self._window.update()

    def close(self) -> None:
        """Destroys the splash window."""
        try:
            if self._window.winfo_exists():
                self._window.destroy()
        except tk.TclError:
            pass
        self._master.update_idletasks()
