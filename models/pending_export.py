"""Pending Proficy export queue entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(slots=True)
class PendingExportChange:
    """One queued Proficy batch export row."""

    vessel: str
    row_data: dict[str, str]
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    baseline: dict[str, str] | None = None
