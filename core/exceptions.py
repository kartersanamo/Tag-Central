"""Core application errors with CLI exit semantics."""

from __future__ import annotations


class TagCentralError(Exception):
    """User or runtime error (CLI exit code 1)."""


class PolicyAbortError(TagCentralError):
    """Operation aborted by policy (CLI exit code 2)."""
