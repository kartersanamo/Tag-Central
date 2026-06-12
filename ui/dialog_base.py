"""Shared modal dialog shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class ModalDialog:
    """Base modal window with standard setup and footer buttons."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        *,
        width: int = 640,
        height: int = 480,
        resizable: bool = False,
    ) -> None:
        self._parent = parent
        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.geometry(f"{width}x{height}")
        self._window.resizable(resizable, resizable)
        self._window.transient(parent)
        self._window.grab_set()

        self.body = ttk.Frame(self._window, padding=14)
        self.body.pack(fill="both", expand=True)
        self.footer = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        self.footer.pack(fill="x")

    @property
    def window(self) -> tk.Toplevel:
        return self._window

    def add_button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        side: str = "left",
        padx: tuple[int, int] = (0, 8),
    ) -> ttk.Button:
        button = ttk.Button(self.footer, text=text, command=command)
        button.pack(side=side, padx=padx)
        return button

    def wait(self) -> None:
        self._window.wait_window()

    def close(self) -> None:
        self._window.destroy()

    def on_close(self, handler: Callable[[], None]) -> None:
        self._window.protocol("WM_DELETE_WINDOW", handler)
