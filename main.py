"""Tag Central executable entrypoint."""

import tkinter as tk

from app_config import APP_TITLE, MIN_WINDOW_SIZE, WINDOW_SIZE
from app_controller import AppController


def main() -> None:
    """Starts the application."""
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry(WINDOW_SIZE)
    root.minsize(*MIN_WINDOW_SIZE)
    AppController(root)
    root.mainloop()


if __name__ == "__main__":
    main()
