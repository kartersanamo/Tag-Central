"""Persistence for tag records."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from models.tag_record import SYNC_PROFICY_ONLY, TagRecord
from services.address_normalizer import is_resolvable_address, normalize_address


class TagRepository:
    """Loads and saves the local CSV tag database."""

    CSV_COLUMNS = (
        "tag_name",
        "description",
        "vessels",
        "proficy_row_data",
        "cimplicity_row_data",
        "cimplicity_pt_id",
        "proficy_name",
        "linked_address",
        "sync_status",
        "link_method",
        "row_data",
    )

    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file

    def load(self) -> dict[str, TagRecord]:
        """Loads all tags from disk."""
        if not self._database_file.exists():
            return {}

        tags: dict[str, TagRecord] = {}
        with self._database_file.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                record = self._record_from_csv_row(row)
                if record is None:
                    continue
                tags[record.tag_name] = record
        return tags

    def save(self, tags: dict[str, TagRecord]) -> None:
        """Persists all tags to disk."""
        self._database_file.parent.mkdir(parents=True, exist_ok=True)

        with self._database_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(self.CSV_COLUMNS))
            writer.writeheader()

            for tag_name in sorted(tags):
                record = tags[tag_name]
                writer.writerow(
                    {
                        "tag_name": record.tag_name,
                        "description": record.description,
                        "vessels": record.vessels_csv(),
                        "proficy_row_data": json.dumps(
                            record.proficy_row_data, ensure_ascii=True
                        ),
                        "cimplicity_row_data": json.dumps(
                            record.cimplicity_row_data, ensure_ascii=True
                        ),
                        "cimplicity_pt_id": record.cimplicity_pt_id,
                        "proficy_name": record.proficy_name,
                        "linked_address": record.linked_address,
                        "sync_status": record.sync_status,
                        "link_method": record.link_method or "",
                        "row_data": json.dumps(
                            record.proficy_row_data, ensure_ascii=True
                        ),
                    }
                )

    def _record_from_csv_row(self, row: dict[str, str]) -> TagRecord | None:
        tag_name = row.get("tag_name", "").strip().upper()
        if not tag_name:
            return None

        description = row.get("description", "").strip().upper()
        vessels = {
            vessel.strip().upper()
            for vessel in row.get("vessels", "").split(";")
            if vessel.strip()
        }

        proficy_row_data = self._parse_row_payload(
            row.get("proficy_row_data", "") or row.get("row_data", "")
        )
        cimplicity_row_data = self._parse_row_payload(row.get("cimplicity_row_data", ""))
        cimplicity_pt_id = row.get("cimplicity_pt_id", "").strip().upper()
        proficy_name = row.get("proficy_name", "").strip().upper() or tag_name
        linked_address = row.get("linked_address", "").strip().upper()
        if linked_address and not is_resolvable_address(linked_address):
            linked_address = ""
        if not linked_address and proficy_row_data:
            candidate = normalize_address(TagRecord._address_from_row(proficy_row_data))
            if is_resolvable_address(candidate):
                linked_address = candidate
        sync_status = row.get("sync_status", "").strip() or SYNC_PROFICY_ONLY
        link_method = row.get("link_method", "").strip() or None

        return TagRecord(
            tag_name=tag_name,
            description=description,
            vessels=vessels,
            proficy_row_data=proficy_row_data,
            cimplicity_row_data=cimplicity_row_data,
            cimplicity_pt_id=cimplicity_pt_id,
            proficy_name=proficy_name,
            linked_address=linked_address,
            sync_status=sync_status,
            link_method=link_method,
        )

    @staticmethod
    def _parse_row_payload(value: str) -> dict[str, str]:
        if not value.strip():
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(key): str(item) for key, item in parsed.items()}
