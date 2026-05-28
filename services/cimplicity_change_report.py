"""Manual Cimplicity change report export."""

from __future__ import annotations

from pathlib import Path

from app_config import EXPORT_FOLDER
from services.pandas_lazy import get_pandas


class CimplicityChangeReport:
    """Writes rows that require manual Cimplicity edits."""

    def __init__(self, export_folder: Path | None = None) -> None:
        self._export_folder = export_folder or EXPORT_FOLDER

    def write_report(
        self,
        vessel: str,
        entries: list[dict[str, str]],
    ) -> Path | None:
        if not entries:
            return None
        pd = get_pandas()
        self._export_folder.mkdir(parents=True, exist_ok=True)
        output_path = self._next_path(vessel)
        frame = pd.DataFrame(entries)
        frame.to_csv(output_path, index=False)
        return output_path

    def _next_path(self, vessel: str) -> Path:
        base = f"{vessel}_CIMPLICITY_MANUAL"
        primary = self._export_folder / f"{base}.csv"
        if not primary.exists():
            return primary
        index = 1
        while True:
            candidate = self._export_folder / f"{base}-{index}.csv"
            if not candidate.exists():
                return candidate
            index += 1
