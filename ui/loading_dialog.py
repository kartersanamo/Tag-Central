"""Simple progress overlay for long-running UI tasks."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ui.ctk_theme import FONT_BODY


class LoadingDialog:
    """Modal-ish loading dialog with status updates and spinner."""

    def __init__(self, parent: ctk.CTk, title: str = "Working...") -> None:
        self._parent = parent
        self._window = ctk.CTkToplevel(parent)
        self._window.title(title)
        self._window.geometry("460x140")
        self._window.resizable(False, False)
        self._window.transient(parent)
        self._window.protocol("WM_DELETE_WINDOW", lambda: None)

        self._status_var = tk.StringVar(value="Starting...")
        frame = ctk.CTkFrame(self._window, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(frame, textvariable=self._status_var, font=FONT_BODY, anchor="w").pack(
            fill="x", pady=(0, 10)
        )
        self._progress = ctk.CTkProgressBar(frame, mode="indeterminate")
        self._progress.pack(fill="x")
        self._progress.start()

    def show(self, status_text: str) -> None:
        self.update_status(status_text)
        self._window.lift()
        self._window.attributes("-topmost", True)
        try:
            self._window.grab_set()
        except tk.TclError:
            pass
        self._window.update()

    def update_status(self, status_text: str) -> None:
        self._status_var.set(status_text)
        self._window.update()

    def close(self) -> None:
        try:
            self._progress.stop()
        except tk.TclError:
            pass
        try:
            if self._window.winfo_exists():
                try:
                    self._window.grab_release()
                except tk.TclError:
                    pass
                self._window.attributes("-topmost", False)
                self._window.destroy()
        except tk.TclError:
            pass
