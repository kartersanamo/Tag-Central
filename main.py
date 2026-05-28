"""Tag Central executable entrypoint."""

from __future__ import annotations

import sys
import tkinter as tk

from app_config import APP_TITLE, MIN_WINDOW_SIZE, WINDOW_SIZE
from app_controller import AppController
from app_identity import (
    APP_VERSION,
    ensure_user_data_layout,
    icon_ico_path,
    icon_png_path,
    is_frozen,
)


def _apply_window_icon(root: tk.Tk) -> None:
    """Sets the window (and taskbar on Windows) icon when assets are available."""
    try:
        if sys.platform == "win32" and icon_ico_path().exists():
            root.iconbitmap(default=str(icon_ico_path()))
            return
        png_path = icon_png_path()
        if png_path.exists():
            icon_image = tk.PhotoImage(file=str(png_path))
            root.iconphoto(True, icon_image)
            root._tag_central_icon = icon_image  # prevent garbage collection
    except tk.TclError:
        pass


def main() -> None:
    """Starts the application."""
    if is_frozen():
        ensure_user_data_layout()

    root = tk.Tk()
    title = APP_TITLE if not APP_VERSION else f"{APP_TITLE} {APP_VERSION}"
    root.title(title)
    root.geometry(WINDOW_SIZE)
    root.minsize(*MIN_WINDOW_SIZE)
    _apply_window_icon(root)
    AppController(root)
    root.mainloop()


if __name__ == "__main__":
    main()
