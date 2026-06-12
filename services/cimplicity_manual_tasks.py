"""Persistent queue of manual Cimplicity updates to verify."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app_config import CIMPLICITY_MANUAL_TASKS_FILE
from models.manual_task import ManualTask


class CimplicityManualTasks:
    """Loads, tracks, and clears manual Cimplicity task acknowledgements."""

    def __init__(self, queue_file: Path | None = None) -> None:
        self._queue_file = queue_file or CIMPLICITY_MANUAL_TASKS_FILE
        self._items: list[ManualTask] = []
        self.load()

    @property
    def items(self) -> list[ManualTask]:
        return list(self._items)

    def pending_count(self) -> int:
        return sum(1 for item in self._items if not item.done)

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
        self._items = [ManualTask.from_dict(item) for item in raw_items if isinstance(item, dict)]

    def save(self) -> None:
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in self._items]
        self._queue_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def add_task(
        self,
        *,
        vessel: str,
        tag_name: str,
        field: str,
        old_value: str,
        new_value: str,
        reason: str,
    ) -> None:
        task = ManualTask(
            task_id=str(uuid.uuid4()),
            vessel=vessel.strip().upper() or "GLOBAL",
            tag_name=tag_name.strip().upper(),
            field=field.strip().lower(),
            old_value=old_value.strip(),
            new_value=new_value.strip(),
            reason=reason.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
            done=False,
        )
        self._items.append(task)
        self.save()

    def set_done(self, task_id: str, done: bool) -> None:
        for item in self._items:
            if item.task_id == task_id:
                item.done = done
                break
        self.save()

    def set_all_done(self, done: bool) -> None:
        for item in self._items:
            item.done = done
        self.save()

    def clear_done(self) -> int:
        before = len(self._items)
        self._items = [item for item in self._items if not item.done]
        cleared = before - len(self._items)
        self.save()
        return cleared

    def clear_all(self) -> int:
        """Removes every task (pending or checked). Returns count removed."""
        count = len(self._items)
        self._items = []
        self.save()
        return count

