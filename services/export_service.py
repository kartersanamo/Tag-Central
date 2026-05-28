"""Export generation for downstream re-import workflows."""

from __future__ import annotations

from pathlib import Path

from services.pandas_lazy import get_pandas


class ExportService:
    """Writes per-vessel export files for tag changes."""

    def __init__(self, export_folder: Path) -> None:
        self._export_folder = export_folder

    def write_exports(self, exports: dict[str, list[dict[str, object]]]) -> list[Path]:
        """Writes export CSV files and returns paths written."""
        pd = get_pandas()
        self._export_folder.mkdir(parents=True, exist_ok=True)
        written_paths: list[Path] = []

        for vessel, changes in exports.items():
            rows = []
            for change in changes:
                row = dict(change["row"])  # type: ignore[arg-type]
                rows.append(row)

            frame = pd.DataFrame(rows)
            output_path = self._next_available_export_path(f"{vessel}_BATCH_EXPORT")
            frame.to_csv(output_path, index=False)
            written_paths.append(output_path)

        return written_paths

    def _next_available_export_path(self, base_name: str) -> Path:
        """Returns a non-overwriting export path with -N suffix if needed."""
        primary = self._export_folder / f"{base_name}.csv"
        if not primary.exists():
            return primary

        index = 1
        while True:
            candidate = self._export_folder / f"{base_name}-{index}.csv"
            if not candidate.exists():
                return candidate
            index += 1
