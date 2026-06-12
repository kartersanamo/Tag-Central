"""Unmatched Cimplicity import queue item."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReviewQueueItem:
    """One Cimplicity-only row awaiting user resolution."""

    vessel: str
    pt_id: str
    description: str
    address: str
    row_data: dict[str, str] = field(default_factory=dict)
    imported_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "vessel": self.vessel,
            "pt_id": self.pt_id,
            "description": self.description,
            "address": self.address,
            "row_data": dict(self.row_data),
            "imported_at": self.imported_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ReviewQueueItem:
        row_data = payload.get("row_data", {})
        return cls(
            vessel=str(payload.get("vessel", "")).strip().upper(),
            pt_id=str(payload.get("pt_id", "")).strip().upper(),
            description=str(payload.get("description", "")).strip().upper(),
            address=str(payload.get("address", "")).strip().upper(),
            row_data=dict(row_data) if isinstance(row_data, dict) else {},
            imported_at=str(payload.get("imported_at", "")),
        )
