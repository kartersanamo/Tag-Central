"""Policy flags for non-interactive imports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImportOptions:
    """CLI/GUI import policy (no stdin prompts)."""

    yes: bool = False
    conflict_action: str = "skip"
    sync_action: str = "skip"
    ambiguous_action: str = "skip"
    descriptions: str = "auto"
