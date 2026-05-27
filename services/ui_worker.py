"""Background worker for CPU-heavy UI preparation."""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable


class UiWorker:
    """Runs a callable on a background thread and delivers result on main thread."""

    def __init__(self, root) -> None:
        self._root = root

    def submit(
        self,
        work: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        result_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        def runner() -> None:
            try:
                result_queue.put(("ok", work()))
            except Exception as error:  # noqa: BLE001
                result_queue.put(("err", error))

        threading.Thread(target=runner, daemon=True).start()

        def poll() -> None:
            try:
                status, payload = result_queue.get_nowait()
            except queue.Empty:
                self._root.after(50, poll)
                return
            if status == "ok":
                on_success(payload)
            elif on_error is not None:
                on_error(payload)  # type: ignore[arg-type]

        self._root.after(50, poll)
