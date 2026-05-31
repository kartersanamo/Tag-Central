"""Tag Central executable entrypoint."""

from __future__ import annotations

import os
import sys

import customtkinter as ctk

from app_identity import APP_NAME, APP_VERSION, ensure_user_data_layout, is_frozen
from ui.ctk_theme import apply_ctk_theme

# Imported at module level so PyInstaller always bundles the full application.
import app_config  # noqa: F401
import app_controller  # noqa: F401


def _apply_window_icon(root: ctk.CTk) -> None:
    """Sets the window (and taskbar on Windows) icon when assets are available."""
    from app_identity import icon_ico_path, icon_png_path

    try:
        if sys.platform == "win32" and icon_ico_path().exists():
            root.iconbitmap(default=str(icon_ico_path()))
            return
        png_path = icon_png_path()
        if png_path.exists():
            icon_image = ctk.PhotoImage(file=str(png_path))
            root.iconphoto(True, icon_image)
            root._tag_central_icon = icon_image  # prevent garbage collection
    except Exception:
        pass


def _show_startup_error(root: ctk.CTk, error: BaseException) -> None:
    """Shows a dialog when the packaged app fails during startup."""
    import traceback
    from tkinter import messagebox

    details = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    try:
        messagebox.showerror(
            f"{APP_NAME} — startup failed",
            "The application could not start.\n\n"
            f"{error}\n\n"
            "See details below and contact support if this continues.\n\n"
            f"{details[:2000]}",
            parent=root,
        )
    except Exception:
        print(details, file=sys.stderr)


def main() -> None:
    """Starts the application with an immediate splash, then loads the main UI."""
    apply_ctk_theme()
    if is_frozen():
        ensure_user_data_layout()

    root = ctk.CTk()
    root.withdraw()
    splash = None

    try:
        from ui.startup_splash import StartupSplash

        splash = StartupSplash(root)
        splash.set_status("Starting Tag Center…")

        splash.set_status("Loading modules…")
        from app_config import MIN_WINDOW_SIZE, WINDOW_SIZE
        from app_controller import AppController  # noqa: F811

        splash.set_status("Preparing workspace…")
        title = APP_NAME if not APP_VERSION else f"{APP_NAME} {APP_VERSION}"
        root.title(title)
        root.geometry(WINDOW_SIZE)
        root.minsize(*MIN_WINDOW_SIZE)
        _apply_window_icon(root)

        def startup_status(message: str) -> None:
            if splash is not None:
                splash.set_status(message)

        controller = AppController(
            root,
            startup_status=startup_status,
            skip_initial_refresh=True,
        )

        splash.set_status("Opening window…")
        splash.close()
        splash = None
        root.deiconify()
        root.update_idletasks()

        controller.finish_startup(startup_status=startup_status)

        root.lift()
        root.focus_force()
        if os.environ.get("TAG_CENTER_QUIT_AFTER_STARTUP"):
            root.after(100, root.quit)
        root.mainloop()
    except Exception as error:
        if splash is not None:
            splash.close()
        root.deiconify()
        _show_startup_error(root, error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
