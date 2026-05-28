"""Deferred pandas import so the GUI can start without loading the full stack."""

from __future__ import annotations

from typing import Any

_PANDAS: Any = None


def get_pandas() -> Any:
    """Returns the pandas module, importing it on first use."""
    global _PANDAS
    if _PANDAS is None:
        import pandas as pd

        _PANDAS = pd
    return _PANDAS
