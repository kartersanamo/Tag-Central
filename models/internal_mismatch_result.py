"""Internal tag mismatch analysis result."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InternalMismatchResult:
    """Maps tags to mismatch groups and types."""

    conflicted_tags: set[str] = field(default_factory=set)
    peers: dict[str, list[str]] = field(default_factory=dict)
    group_labels: dict[str, str] = field(default_factory=dict)
    mismatch_types: dict[str, str] = field(default_factory=dict)
