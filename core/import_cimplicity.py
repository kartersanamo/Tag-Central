"""Headless Cimplicity CSV import."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app_config import BULK_IMPORT_BACKUP_THRESHOLD
from core.descriptions import fill_missing_descriptions_for_field
from core.exceptions import TagCentralError
from core.import_options import ImportOptions
from models.review_queue_item import ReviewQueueItem
from services.debug_logger import debug_logger

if TYPE_CHECKING:
    from core.tag_central_app import TagCentralApp


def _map_ambiguous_action(action_name: str) -> str:
    action = action_name.strip().lower()
    if action in {"align_selected", "merge_then_align"}:
        return "align_proficy"
    if action == "link_only_selected":
        return "link_only"
    if action == "flag_manual_cimplicity":
        return "flag_manual_cimplicity"
    return "skip"


def run_cimplicity_import(
    app: TagCentralApp,
    file_path: str,
    vessel: str,
    options: ImportOptions,
) -> dict[str, object]:
    """Imports Cimplicity rows with uniform sync/ambiguous policy."""
    vessel = vessel.strip().upper()
    if not vessel:
        raise TagCentralError("Vessel name cannot be empty.")
    path = Path(file_path)
    if not path.exists():
        raise TagCentralError(f"File not found: {file_path}")

    debug_logger.log(
        "import_flow",
        "Cimplicity import requested",
        vessel=vessel,
        path=file_path,
        cli=options.yes,
    )

    raw_rows = app.cimplicity_loader.load_rows(str(path))
    cimplicity_desc_summary: dict[str, object] = {
        "rows_missing_description_filled": 0,
        "pending_manual_tasks": [],
    }
    pending_tasks = cimplicity_desc_summary.setdefault("pending_manual_tasks", [])
    assert isinstance(pending_tasks, list)

    def queue_manual_task(
        pt_id: str, old_value: str, new_value: str, row_index: int
    ) -> None:
        pending_tasks.append(
            {
                "vessel": vessel,
                "tag_name": pt_id,
                "field": "description",
                "old_value": old_value,
                "new_value": new_value,
                "reason": (
                    "Cimplicity import row had empty DESC; enter this description "
                    f"in Cimplicity (row {row_index + 1})"
                ),
            }
        )

    fill_summary: dict[str, int] = {"rows_missing_description_filled": 0}
    if options.yes:
        fill_missing_descriptions_for_field(
            app,
            rows=raw_rows,
            summary=fill_summary,
            tag_field="PT_ID",
            description_field="DESC",
            descriptions_mode=options.descriptions,
            on_apply=queue_manual_task,
        )
    else:
        # Dry-run: detect missing descriptions without filling
        missing = sum(
            1
            for row in raw_rows
            if row.get("PT_ID", "").strip()
            and not row.get("DESC", "").strip()
        )
        fill_summary["rows_missing_description_filled"] = 0
        if missing and options.descriptions == "fail":
            from core.exceptions import PolicyAbortError

            raise PolicyAbortError(f"{missing} Cimplicity row(s) missing DESC")

    cimplicity_desc_summary["rows_missing_description_filled"] = fill_summary[
        "rows_missing_description_filled"
    ]

    prepared = app.cross_program.prepare_cimplicity_rows(raw_rows)
    analysis = app.cross_program.analyze_cimplicity_import(app.tags, prepared, vessel)

    dry_lines = list(analysis.report_lines) + [
        "",
        f"Descriptions generated (manual tasks): "
        f"{int(cimplicity_desc_summary['rows_missing_description_filled'])}",
        f"Estimated review queue additions: {analysis.review_queue_added}",
        f"Rows needing resolver: {len(analysis.actionable)}",
        f"Rows already aligned (auto-pass): {analysis.linked_synced}",
    ]

    if not options.yes:
        return {
            "vessel": vessel,
            "file": str(path),
            "total_rows": len(prepared),
            "report_lines": dry_lines,
            "dry_run": True,
            "message": "Re-run with --yes to apply import.",
        }

    for task in pending_tasks:
        if isinstance(task, dict):
            app.manual_tasks.add_task(**task)

    if len(prepared) >= BULK_IMPORT_BACKUP_THRESHOLD:
        app.auto_backup_before_bulk("cimplicity_import")

    app.last_cimplicity_link_report = list(analysis.report_lines)

    summary: dict[str, int] = {
        "total_rows": len(prepared),
        "linked_synced": 0,
        "auto_aligned": 0,
        "review_queue_added": analysis.review_queue_added,
        "actionable": len(analysis.actionable),
        "skipped": 0,
        "proficy_exports_queued": 0,
        "manual_cimplicity_flags": 0,
        "rows_missing_description_filled": int(
            cimplicity_desc_summary["rows_missing_description_filled"]
        ),
    }

    sync_action = options.sync_action.strip().lower()
    ambiguous_action = options.ambiguous_action.strip().lower()
    valid_sync = {"align_proficy", "link_only", "flag_manual_cimplicity", "skip"}
    valid_ambiguous = {
        "align_selected",
        "merge_then_align",
        "link_only_selected",
        "flag_manual_cimplicity",
        "skip",
    }
    if sync_action not in valid_sync:
        raise TagCentralError(
            f"Invalid sync_action: {options.sync_action!r}. "
            f"Use one of: {', '.join(sorted(valid_sync))}."
        )
    if ambiguous_action not in valid_ambiguous:
        raise TagCentralError(
            f"Invalid ambiguous_action: {options.ambiguous_action!r}. "
            f"Use one of: {', '.join(sorted(valid_ambiguous))}."
        )

    decisions: list[dict[str, str]] = []
    for action in analysis.actionable:
        if action.issue.startswith("ambiguous_address:"):
            candidate_tags = action.issue.split(":", 1)[1]
            candidates = [
                item.strip().upper()
                for item in candidate_tags.split(",")
                if item.strip()
            ]
            selected_tag = action.existing_tag or (candidates[0] if candidates else "")
            if selected_tag not in candidates and candidates:
                selected_tag = candidates[0]

            if ambiguous_action == "merge_then_align" and selected_tag in app.tags:
                for candidate in candidates:
                    if candidate == selected_tag or candidate not in app.tags:
                        continue
                    try:
                        merged = app.merge_service.merge_tags(
                            app.tags, selected_tag, candidate
                        )
                    except KeyError:
                        continue
                    export_row = merged.proficy_export_row()
                    for tag_vessel in merged.vessels or {"GLOBAL"}:
                        app.queue_change(tag_vessel, export_row)

            base_action = _map_ambiguous_action(ambiguous_action)
            decisions.append(
                {
                    "action": base_action,
                    "pt_id": action.pt_id,
                    "row_index": str(action.row_index),
                    "existing_tag": selected_tag,
                    "issue": action.issue,
                }
            )
            continue

        decisions.append(
            {
                "action": sync_action,
                "pt_id": action.pt_id,
                "cimplicity_description": action.cimplicity_description,
                "address": action.address,
                "existing_tag": action.existing_tag,
                "existing_description": action.existing_description,
                "issue": action.issue,
                "row_index": str(action.row_index),
                "row_data": str(action.row_data),
            }
        )

    row_by_index = {row.row_index: row for row in prepared}
    row_by_pt_id = {row.pt_id: row for row in prepared}

    for decision in decisions:
        row_index = int(decision.get("row_index", -1))
        row = row_by_index.get(row_index) or row_by_pt_id.get(
            str(decision.get("pt_id", "")).strip().upper()
        )
        if row is None:
            continue
        action = decision.get("action", "skip")
        if action == "skip":
            summary["skipped"] += 1
            continue

        stale_tag = str(decision.get("existing_tag", "")).strip().upper()
        link = app.cross_program._linker.link_cimplicity_row(
            app.tags, row.pt_id, row.address
        )
        canonical_tag = app.cross_program.resolve_tag_key(
            app.tags, row, link, preferred_key=stale_tag or None
        )
        if canonical_tag is None and action not in {"skip", "flag_manual_cimplicity"}:
            summary["skipped"] += 1
            continue

        changed, export_row = app.cross_program.apply_cimplicity_row(
            app.tags,
            row,
            vessel,
            action,
            canonical_tag=canonical_tag,
        )
        if action == "flag_manual_cimplicity":
            summary["manual_cimplicity_flags"] += 1
            app.cimplicity_manual_entries.append(
                {
                    "PT_ID": row.pt_id,
                    "field": "manual_review",
                    "current": row.description,
                    "recommended": row.description,
                    "reason": decision.get("issue", "flagged"),
                }
            )
            continue

        if action == "align_proficy" and changed:
            summary["auto_aligned"] += 1
            if export_row:
                app.queue_change(vessel=vessel, row_data=export_row)
                summary["proficy_exports_queued"] += 1
        elif action == "link_only" and changed:
            summary["linked_synced"] += 1

    for row in prepared:
        if any(int(d.get("row_index", -1)) == row.row_index for d in decisions):
            continue
        link = app.cross_program._linker.link_cimplicity_row(
            app.tags, row.pt_id, row.address
        )
        if link.canonical_tag and not app.cross_program._detect_issues(
            app.tags[link.canonical_tag], row
        ):
            _, export_row = app.cross_program.apply_cimplicity_row(
                app.tags,
                row,
                vessel,
                "align_proficy",
                canonical_tag=link.canonical_tag,
            )
            summary["auto_aligned"] += 1
            if export_row:
                app.queue_change(vessel=vessel, row_data=export_row)
                summary["proficy_exports_queued"] += 1

    for row in prepared:
        link = app.cross_program._linker.link_cimplicity_row(
            app.tags, row.pt_id, row.address
        )
        if link.canonical_tag or link.ambiguous_tags:
            continue
        app.cross_program.review_queue.add(
            ReviewQueueItem(
                vessel=vessel,
                pt_id=row.pt_id,
                description=row.description,
                address=row.address,
                row_data=row.row_data,
                imported_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    app.persist_tags()
    app.recalculate_conflicted_tags()

    manual_report_path = None
    if app.cimplicity_manual_entries:
        manual_report_path = app.cimplicity_report.write_report(
            "GLOBAL", app.cimplicity_manual_entries
        )
        app.cimplicity_manual_entries.clear()

    debug_logger.log(
        "import_flow",
        "Cimplicity import complete",
        vessel=vessel,
        total_rows=summary["total_rows"],
        exports_pending=app.export_queue.count(),
    )

    return {
        "vessel": vessel,
        "file": str(path),
        "dry_run": False,
        "summary": summary,
        "report_lines": list(app.last_cimplicity_link_report),
        "manual_report_path": str(manual_report_path) if manual_report_path else None,
        "pending_exports": app.export_queue.count(),
    }
