"""Tag Central executable entrypoint."""

from __future__ import annotations

import os
import sys
import tkinter as tk

from app_identity import APP_NAME, APP_VERSION, ensure_user_data_layout, is_frozen


def _apply_window_icon(root: tk.Tk) -> None:
    """Sets the window (and taskbar on Windows) icon when assets are available."""
    from app_identity import icon_ico_path, icon_png_path

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
    """Starts the application with an immediate splash, then loads the main UI."""
    if is_frozen():
        ensure_user_data_layout()

    root = tk.Tk()
    root.withdraw()

    from ui.startup_splash import StartupSplash

    splash = StartupSplash(root)
    splash.set_status("Starting Tag Center…")

    splash.set_status("Loading modules…")
    from app_config import MIN_WINDOW_SIZE, WINDOW_SIZE
    from app_controller import AppController

    splash.set_status("Preparing workspace…")
    title = APP_NAME if not APP_VERSION else f"{APP_NAME} {APP_VERSION}"
    root.title(title)
    root.geometry(WINDOW_SIZE)
    root.minsize(*MIN_WINDOW_SIZE)
    _apply_window_icon(root)

    def startup_status(message: str) -> None:
        splash.set_status(message)

    controller = AppController(
        root,
        startup_status=startup_status,
        skip_initial_refresh=True,
    )

    splash.set_status("Opening window…")
    splash.close()
    root.deiconify()
    root.update_idletasks()

    controller.finish_startup(startup_status=startup_status)

    root.lift()
    root.focus_force()
    if os.environ.get("TAG_CENTER_QUIT_AFTER_STARTUP"):
        root.after(100, root.quit)
    root.mainloop()


if __name__ == "__main__":
    main()
