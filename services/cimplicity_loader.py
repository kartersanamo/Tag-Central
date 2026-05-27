"""Cimplicity Shared Name File import utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from services.address_normalizer import normalize_address


class CimplicityLoader:
    """Loads Cimplicity 6.x Shared Name File CSV exports."""

    REQUIRED_COLUMNS = {"PT_ID", "DESC"}

    def load_rows(self, file_path: str) -> list[dict[str, str]]:
        """Loads Cimplicity rows, skipping comment header lines."""
        path = Path(file_path)
        if path.suffix.lower() != ".csv":
            raise ValueError("Cimplicity imports must be .csv Shared Name Files.")

        raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        data_lines = [line for line in raw_lines if not line.startswith("##")]
        if not data_lines:
            raise ValueError("Cimplicity file has no data rows.")

        frame = pd.read_csv(
            pd.io.common.StringIO("\n".join(data_lines)),
            dtype=str,
            keep_default_na=False,
        )
        frame.columns = frame.columns.str.strip()
        self._validate_schema(frame)

        rows: list[dict[str, str]] = []
        for _, series in frame.iterrows():
            row = {
                key: ("" if pd.isna(value) else str(value).strip())
                for key, value in series.to_dict().items()
            }
            pt_id = row.get("PT_ID", "").strip().upper()
            if not pt_id:
                continue
            row["PT_ID"] = pt_id
            row["DESC"] = row.get("DESC", "").strip()
            if row.get("ADDR", "").strip():
                row["ADDR"] = normalize_address(row["ADDR"])
            rows.append(row)
        return rows

    def _validate_schema(self, frame: pd.DataFrame) -> None:
        columns = {str(column).strip() for column in frame.columns.tolist()}
        missing = self.REQUIRED_COLUMNS - columns
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                "Cimplicity file is missing required columns: "
                f"{missing_text}. Expected PT_ID and DESC."
            )
