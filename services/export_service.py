"""Export generation for downstream re-import workflows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class ExportService:
    """Writes per-vessel export files for tag changes."""

    def __init__(self, export_folder: Path) -> None:
        self._export_folder = export_folder

    def write_exports(self, exports: dict[str, list[dict[str, object]]]) -> list[Path]:
        """Writes export CSV files and returns paths written."""
        self._export_folder.mkdir(parents=True, exist_ok=True)
        written_paths: list[Path] = []

        for vessel, changes in exports.items():
            rows = []
            for change in changes:
                row = dict(change["row"])  # type: ignore[arg-type]
                rows.append(row)

            frame = pd.DataFrame(rows)
            output_path = self._export_folder / f"{vessel}_BATCH_EXPORT.csv"
            frame.to_csv(output_path, index=False)
            written_paths.append(output_path)

        return written_paths
