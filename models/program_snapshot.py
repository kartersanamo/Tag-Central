"""Per-program tag snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

ProgramKind = Literal["proficy", "cimplicity"]


@dataclass(slots=True)
class ProgramSnapshot:
    """Stores imported row data for one SCADA program."""

    program: ProgramKind
    tag_id: str
    description: str
    address: str
    row_data: dict[str, str] = field(default_factory=dict)
    vessel: str = ""
    imported_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "program": self.program,
            "tag_id": self.tag_id,
            "description": self.description,
            "address": self.address,
            "row_data": dict(self.row_data),
            "vessel": self.vessel,
            "imported_at": self.imported_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ProgramSnapshot:
        row_data = payload.get("row_data", {})
        return cls(
            program=str(payload.get("program", "proficy")),  # type: ignore[arg-type]
            tag_id=str(payload.get("tag_id", "")).strip().upper(),
            description=str(payload.get("description", "")).strip().upper(),
            address=str(payload.get("address", "")).strip().upper(),
            row_data=dict(row_data) if isinstance(row_data, dict) else {},
            vessel=str(payload.get("vessel", "")).strip().upper(),
            imported_at=str(payload.get("imported_at", "")),
        )
