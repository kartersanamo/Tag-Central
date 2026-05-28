"""Structured debug logger with master/category toggles."""

from __future__ import annotations

from datetime import datetime

from app_config import DEBUG_LOGGING_ENABLED, DEBUG_LOGGING_OPTIONS


class DebugLogger:
    """Prints timestamped debug lines when enabled by config."""

    def __init__(
        self,
        *,
        enabled: bool = DEBUG_LOGGING_ENABLED,
        options: dict[str, bool] | None = None,
    ) -> None:
        self._enabled = enabled
        self._options = dict(options or DEBUG_LOGGING_OPTIONS)

    def is_enabled(self, category: str) -> bool:
        """Returns True when both master and category toggles are on."""
        return self._enabled and bool(self._options.get(category, False))

    def log(self, category: str, message: str, **fields: object) -> None:
        """Prints one structured debug line."""
        if not self.is_enabled(category):
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = " ".join(
            f"{key}={self._format_value(value)}" for key, value in fields.items()
        )
        suffix = f" {payload}" if payload else ""
        print(f"[DEBUG {timestamp}] [{category}] {message}{suffix}")

    @staticmethod
    def _format_value(value: object) -> str:
        if isinstance(value, str):
            escaped = value.replace("\n", "\\n")
            return f"'{escaped}'"
        if isinstance(value, (list, tuple, set)):
            parts = ", ".join(str(item) for item in value)
            return f"[{parts}]"
        return str(value)


debug_logger = DebugLogger()

