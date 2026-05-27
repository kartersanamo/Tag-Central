"""Persistence for tag records."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from models.tag_record import TagRecord


class TagRepository:
    """Loads and saves the local CSV tag database."""

    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file

    def load(self) -> dict[str, TagRecord]:
        """Loads all tags from disk."""
        if not self._database_file.exists():
            return {}

        tags: dict[str, TagRecord] = {}
        with self._database_file.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                tag_name = row.get("tag_name", "").strip().upper()
                if not tag_name:
                    continue

                description = row.get("description", "").strip().upper()
                vessels = {
                    vessel.strip().upper()
                    for vessel in row.get("vessels", "").split(";")
                    if vessel.strip()
                }
                row_data = self._safe_parse_json(row.get("row_data", ""))

                tags[tag_name] = TagRecord(
                    tag_name=tag_name,
                    description=description,
                    vessels=vessels,
                    row_data=row_data,
                )

        return tags

    def save(self, tags: dict[str, TagRecord]) -> None:
        """Persists all tags to disk."""
        self._database_file.parent.mkdir(parents=True, exist_ok=True)

        with self._database_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["tag_name", "description", "vessels", "row_data"])

            for tag_name in sorted(tags):
                record = tags[tag_name]
                writer.writerow(
                    [
                        record.tag_name,
                        record.description,
                        record.vessels_csv(),
                        json.dumps(record.row_data, ensure_ascii=True),
                    ]
                )

    @staticmethod
    def _safe_parse_json(value: str) -> dict[str, str]:
        if not value.strip():
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
