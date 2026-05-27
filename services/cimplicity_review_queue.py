"""Persistence for unmatched Cimplicity import rows."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app_config import CIMPLICITY_REVIEW_QUEUE_FILE


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


class CimplicityReviewQueue:
    """Stores and loads unmatched Cimplicity rows."""

    def __init__(self, queue_file: Path | None = None) -> None:
        self._queue_file = queue_file or CIMPLICITY_REVIEW_QUEUE_FILE
        self._items: list[ReviewQueueItem] = []
        self.load()

    @property
    def items(self) -> list[ReviewQueueItem]:
        return list(self._items)

    def count(self) -> int:
        return len(self._items)

    def load(self) -> None:
        if not self._queue_file.exists():
            self._items = []
            return
        try:
            payload = json.loads(self._queue_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._items = []
            return
        raw_items = payload if isinstance(payload, list) else payload.get("items", [])
        self._items = [
            ReviewQueueItem.from_dict(item)
            for item in raw_items
            if isinstance(item, dict)
        ]

    def save(self) -> None:
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in self._items]
        self._queue_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def add(self, item: ReviewQueueItem) -> None:
        """Adds or replaces a queue item for the same vessel + PT_ID."""
        self._items = [
            existing
            for existing in self._items
            if not (existing.vessel == item.vessel and existing.pt_id == item.pt_id)
        ]
        self._items.append(item)
        self.save()

    def remove(self, vessel: str, pt_id: str) -> None:
        self.remove_many([(vessel, pt_id)])

    def remove_many(self, keys: list[tuple[str, str]]) -> int:
        """Removes multiple queue entries in one write. Returns count removed."""
        if not keys:
            return 0
        key_set = {
            (vessel.strip().upper(), pt_id.strip().upper()) for vessel, pt_id in keys
        }
        before = len(self._items)
        self._items = [
            item
            for item in self._items
            if (item.vessel, item.pt_id) not in key_set
        ]
        removed = before - len(self._items)
        if removed:
            self.save()
        return removed

    def clear_vessel(self, vessel: str) -> None:
        vessel = vessel.strip().upper()
        self._items = [item for item in self._items if item.vessel != vessel]
        self.save()
