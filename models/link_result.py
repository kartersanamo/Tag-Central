"""Cimplicity row link result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LinkMethod = Literal["exact_id", "address", "alias", "cimplicity_pt_id", "manual"]


@dataclass(slots=True)
class LinkResult:
    """Result of attempting to link a Cimplicity row to the database."""

    canonical_tag: str | None
    method: LinkMethod | None
    ambiguous_tags: list[str]
