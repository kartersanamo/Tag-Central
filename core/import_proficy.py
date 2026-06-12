"""Headless Proficy spreadsheet import."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app_config import BULK_IMPORT_BACKUP_THRESHOLD
from core.descriptions import fill_missing_descriptions_for_field
from core.exceptions import TagCentralError
from core.import_options import ImportOptions
from services.debug_logger import debug_logger

if TYPE_CHECKING:
    from core.tag_central_app import TagCentralApp


def proficy_dry_run(app: TagCentralApp, file_path: str, vessel: str) -> dict[str, object]:
    """Analyzes import without mutating data."""
    vessel = vessel.strip().upper()
    if not vessel:
        raise TagCentralError("Vessel name cannot be empty.")
    path = Path(file_path)
    if not path.exists():
        raise TagCentralError(f"File not found: {file_path}")

    rows = app.loader.load_rows(str(path))
    analysis = app.proficy_analyzer.analyze(app.tags, rows, vessel)
    return {
        "vessel": vessel,
        "file": str(path),
        "total_rows": len(rows),
        "analysis_lines": list(analysis.lines),
        "estimated_export_rows": analysis.estimated_export_rows,
        "dry_run": True,
    }


def run_proficy_import(
    app: TagCentralApp,
    file_path: str,
    vessel: str,
    options: ImportOptions,
) -> dict[str, object]:
    """Imports Proficy rows with uniform conflict policy."""
    vessel = vessel.strip().upper()
    if not vessel:
        raise TagCentralError("Vessel name cannot be empty.")
    path = Path(file_path)
    if not path.exists():
        raise TagCentralError(f"File not found: {file_path}")

    debug_logger.log(
        "import_flow",
        "Proficy import requested",
        vessel=vessel,
        path=file_path,
        cli=options.yes,
    )

    rows = app.loader.load_rows(str(path))
    original_rows = [dict(row) for row in rows]

    if not options.yes:
        analysis = app.proficy_analyzer.analyze(app.tags, rows, vessel)
        return {
            "vessel": vessel,
            "file": str(path),
            "total_rows": len(rows),
            "analysis_lines": list(analysis.lines),
            "estimated_export_rows": analysis.estimated_export_rows,
            "dry_run": True,
            "message": "Re-run with --yes to apply import.",
        }

    summary: dict[str, int] = {
        "total_rows": len(rows),
        "rows_missing_name": 0,
        "rows_missing_description_filled": 0,
        "unchanged_matches": 0,
        "conflicts_detected": 0,
        "skipped_by_user": 0,
        "resolved_use_imported": 0,
        "resolved_use_existing": 0,
        "resolved_keep_both": 0,
        "new_tags_created": 0,
        "existing_tags_updated": 0,
        "merged_to_existing": 0,
    }

    if len(rows) >= BULK_IMPORT_BACKUP_THRESHOLD:
        app.auto_backup_before_bulk("proficy_import")

    fill_missing_descriptions_for_field(
        app,
        rows=rows,
        summary=summary,
        tag_field="Name",
        description_field="Description",
        descriptions_mode=options.descriptions,
    )

    pending_conflicts: list[dict[str, object]] = []
    app.conflicted_tags = set()

    for row_index, row_data in enumerate(rows):
        imported_tag = row_data.get("Name", "").strip().upper()
        imported_description = row_data.get("Description", "").strip().upper()
        if not imported_tag:
            summary["rows_missing_name"] += 1
            continue

        existing_same_tag = app.tags.get(imported_tag)
        before_export = (
            existing_same_tag.proficy_export_row()
            if existing_same_tag is not None
            else None
        )
        if (
            existing_same_tag is not None
            and existing_same_tag.description == imported_description
        ):
            summary["unchanged_matches"] += 1

        conflict = app.sync.find_conflict(
            app.tags,
            imported_tag=imported_tag,
            imported_description=imported_description,
        )

        if conflict is None:
            was_new = before_export is None
            app.cross_program.import_proficy_row(
                app.tags,
                tag_name=imported_tag,
                description=imported_description,
                vessel=vessel,
                row_data=row_data,
            )
            if was_new:
                summary["new_tags_created"] += 1
            else:
                summary["existing_tags_updated"] += 1
            record = app.tags[imported_tag]
            after_export = record.proficy_export_row()
            if was_new:
                app.queue_change_if_different(
                    vessel=vessel,
                    original_row=original_rows[row_index],
                    updated_row=after_export,
                )
            elif before_export is not None:
                app.queue_change_if_different(
                    vessel=vessel,
                    original_row=before_export,
                    updated_row=after_export,
                )
            continue

        summary["conflicts_detected"] += 1
        existing_tag, existing_record = conflict
        pending_conflicts.append(
            {
                "imported_tag": imported_tag,
                "imported_description": imported_description,
                "existing_tag": existing_tag,
                "existing_description": existing_record.description,
                "row_data": row_data,
                "existing_same_tag": existing_same_tag,
                "row_index": row_index,
            }
        )

    action = options.conflict_action.strip().lower()
    for conflict in pending_conflicts:
        imported_tag = str(conflict["imported_tag"])
        imported_description = str(conflict["imported_description"])
        existing_tag = str(conflict["existing_tag"])
        row_data = dict(conflict["row_data"])  # type: ignore[arg-type]
        existing_same_tag = conflict["existing_same_tag"]
        row_index = int(conflict["row_index"])
        original_row = original_rows[row_index]

        if action == "skip":
            summary["skipped_by_user"] += 1
            continue

        if action == "use_imported":
            app.sync.add_or_update_imported(
                app.tags,
                tag_name=imported_tag,
                description=imported_description,
                vessel=vessel,
                row_data=row_data,
            )
            summary["resolved_use_imported"] += 1
            if existing_same_tag is None:
                summary["new_tags_created"] += 1
            else:
                summary["existing_tags_updated"] += 1
            updated_row = dict(row_data)
            updated_row["Name"] = imported_tag
            updated_row["Description"] = imported_description
            app.queue_change_if_different(
                vessel=vessel,
                original_row=original_row,
                updated_row=updated_row,
            )
            app.conflicted_tags.add(imported_tag)
            continue

        if action == "use_existing":
            app.sync.add_vessel_to_existing(app.tags, existing_tag, vessel)
            summary["resolved_use_existing"] += 1
            summary["merged_to_existing"] += 1
            updated_row = dict(row_data)
            updated_row["Name"] = existing_tag
            updated_row["Description"] = app.tags[existing_tag].description
            app.queue_change_if_different(
                vessel=vessel,
                original_row=original_row,
                updated_row=updated_row,
            )
            app.conflicted_tags.add(existing_tag)
            continue

        if action == "keep_both":
            new_tag = app.sync.unique_suffix_name(app.tags, imported_tag)
            app.sync.add_or_update_imported(
                app.tags,
                tag_name=new_tag,
                description=imported_description,
                vessel=vessel,
                row_data=row_data,
            )
            summary["resolved_keep_both"] += 1
            summary["new_tags_created"] += 1
            updated_row = dict(row_data)
            updated_row["Name"] = new_tag
            updated_row["Description"] = imported_description
            app.queue_change_if_different(
                vessel=vessel,
                original_row=original_row,
                updated_row=updated_row,
            )
            app.conflicted_tags.add(existing_tag)
            app.conflicted_tags.add(new_tag)
            continue

        raise TagCentralError(
            f"Invalid conflict_action: {options.conflict_action!r}. "
            "Use skip, use_imported, use_existing, or keep_both."
        )

    app.persist_tags()
    app.recalculate_conflicted_tags()

    debug_logger.log(
        "import_flow",
        "Proficy import complete",
        vessel=vessel,
        total_rows=summary["total_rows"],
        conflicts_detected=summary["conflicts_detected"],
        exports_pending=app.export_queue.count(),
    )

    return {
        "vessel": vessel,
        "file": str(path),
        "dry_run": False,
        "summary": summary,
        "pending_exports": app.export_queue.count(),
        "pending_vessels": app.export_queue.vessel_count(),
    }
