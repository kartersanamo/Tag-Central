"""Read-only analysis for Proficy spreadsheet imports."""

from __future__ import annotations

from dataclasses import dataclass, field

from models.tag_record import TagRecord
from services.export_queue_service import export_fields_for_compare
from services.tag_sync_service import TagSyncService


@dataclass
class ProficyImportAnalysis:
    """Dry-run summary for a Proficy import."""

    total_rows: int = 0
    rows_missing_name: int = 0
    rows_missing_description: int = 0
    new_tags: int = 0
    updated_unchanged: int = 0
    updated_with_export: int = 0
    conflicts: int = 0
    estimated_export_rows: int = 0
    lines: list[str] = field(default_factory=list)


class ProficyImportAnalyzer:
    """Simulates Proficy import without mutating tags."""

    def __init__(self, sync_service: TagSyncService | None = None) -> None:
        self._sync = sync_service or TagSyncService()

    def analyze(
        self,
        tags: dict[str, TagRecord],
        rows: list[dict[str, str]],
        vessel: str,
    ) -> ProficyImportAnalysis:
        analysis = ProficyImportAnalysis(total_rows=len(rows))
        for row in rows:
            imported_tag = row.get("Name", "").strip().upper()
            imported_description = row.get("Description", "").strip().upper()
            if not imported_tag:
                analysis.rows_missing_name += 1
                continue
            if not imported_description:
                analysis.rows_missing_description += 1

            existing = tags.get(imported_tag)
            before_export = existing.proficy_export_row() if existing else None

            if (
                existing is not None
                and existing.description == imported_description
            ):
                analysis.updated_unchanged += 1

            conflict = self._sync.find_conflict(
                tags, imported_tag=imported_tag, imported_description=imported_description
            )
            if conflict is not None:
                analysis.conflicts += 1
                continue

            if before_export is None:
                analysis.new_tags += 1
                after_fields = export_fields_for_compare(
                    {
                        "Name": imported_tag,
                        "Description": imported_description or row.get("Description", ""),
                        **row,
                    }
                )
                original_fields = export_fields_for_compare(row)
                if after_fields != original_fields:
                    analysis.estimated_export_rows += 1
            else:
                after_fields = export_fields_for_compare(
                    {
                        **row,
                        "Name": imported_tag,
                        "Description": imported_description,
                    }
                )
                if export_fields_for_compare(before_export) != after_fields:
                    analysis.updated_with_export += 1
                    analysis.estimated_export_rows += 1

        analysis.lines = [
            f"Total rows: {analysis.total_rows}",
            f"New tags: {analysis.new_tags}",
            f"Updated (no export): {analysis.updated_unchanged}",
            f"Updated (will queue export): {analysis.updated_with_export}",
            f"Import conflicts (need resolver): {analysis.conflicts}",
            f"Rows missing name: {analysis.rows_missing_name}",
            f"Rows missing description: {analysis.rows_missing_description}",
            f"Estimated Proficy export rows: {analysis.estimated_export_rows}",
        ]
        return analysis
