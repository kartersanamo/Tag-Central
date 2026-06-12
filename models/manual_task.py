"""Manual Cimplicity update task."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class ManualTask:
    """One manual Cimplicity update task."""

    task_id: str
    vessel: str
    tag_name: str
    field: str
    old_value: str
    new_value: str
    reason: str
    created_at: str
    done: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "vessel": self.vessel,
            "tag_name": self.tag_name,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "created_at": self.created_at,
            "done": self.done,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ManualTask:
        return cls(
            task_id=str(payload.get("task_id", "")) or str(uuid.uuid4()),
            vessel=str(payload.get("vessel", "")).strip().upper(),
            tag_name=str(payload.get("tag_name", "")).strip().upper(),
            field=str(payload.get("field", "")).strip().lower(),
            old_value=str(payload.get("old_value", "")).strip(),
            new_value=str(payload.get("new_value", "")).strip(),
            reason=str(payload.get("reason", "")).strip(),
            created_at=str(payload.get("created_at", "")),
            done=bool(payload.get("done", False)),
        )
