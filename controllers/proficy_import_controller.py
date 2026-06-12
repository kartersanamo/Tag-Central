"""ProficyImport orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

from tkinter import filedialog, messagebox, simpledialog

from app_config import BULK_IMPORT_BACKUP_THRESHOLD
from services.debug_logger import debug_logger
from ui.conflict_dialog import ConflictDialog
from ui.import_dry_run_dialog import ImportDryRunDialog
from ui.loading_dialog import LoadingDialog
from ui.missing_description_dialog import MissingDescriptionDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class ProficyImportController(ControllerBase):
    """Extracted from AppController — proficy_import_controller."""

    def import_proficy_spreadsheet(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Proficy Spreadsheet",
            filetypes=[
                ("Spreadsheet Files", "*.xlsx *.xls *.csv"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
            ],
        )
        if not file_path:
            return

        vessel = simpledialog.askstring("Vessel Name", "Enter vessel name:")
        if not vessel:
            return
        vessel = vessel.strip().upper()
        if not vessel:
            messagebox.showwarning("Invalid Vessel", "Vessel name cannot be empty.")
            return
        debug_logger.log(
            "import_flow",
            "Cimplicity import requested",
            vessel=vessel,
            path=file_path,
        )
        debug_logger.log(
            "import_flow",
            "Proficy import requested",
            vessel=vessel,
            path=file_path,
        )

        loading_read = LoadingDialog(self._window.root, title="Importing Proficy...")
        loading_read.show("Loading Proficy spreadsheet...")
        try:
            try:
                rows = self._loader.load_rows(file_path)
            except Exception as error:
                messagebox.showerror("Import Error", str(error))
                return

            loading_read.update_status(f"Loaded {len(rows)} rows. Preparing import...")
            original_rows = [dict(row) for row in rows]
        finally:
            loading_read.close()

        summary = {
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

        analysis = self._proficy_analyzer.analyze(self._tags, rows, vessel)
        dry_lines = analysis.lines + [
            "",
            "Note: Proficy import conflicts (if any) are resolved in a second dialog after Apply.",
        ]
        if not ImportDryRunDialog(
            self._window.root, "Proficy Import Preview", dry_lines
        ).show():
            debug_logger.log(
                "import_flow",
                "Proficy import cancelled at preview",
                vessel=vessel,
            )
            return
        if analysis.estimated_export_rows >= BULK_IMPORT_BACKUP_THRESHOLD:
            self._app._auto_backup_before_bulk("proficy_import")

        if not self._fill_missing_descriptions(rows, summary):
            debug_logger.log(
                "import_flow",
                "Proficy import cancelled in description review",
                vessel=vessel,
            )
            return

        pending_conflicts: list[dict[str, object]] = []
        self._conflicted_tags = set()

        loading_merge = LoadingDialog(self._window.root, title="Importing Proficy...")
        loading_merge.show("Merging imported rows...")
        try:
            for row_index, row_data in enumerate(rows):
                if row_index == 0 or row_index % 250 == 0:
                    loading_merge.update_status(f"Merging rows... {row_index + 1}/{len(rows)}")
                imported_tag = row_data.get("Name", "").strip().upper()
                imported_description = row_data.get("Description", "").strip().upper()
                if not imported_tag:
                    summary["rows_missing_name"] += 1
                    continue

                existing_same_tag = self._tags.get(imported_tag)
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

                conflict = self._sync.find_conflict(
                    self._tags,
                    imported_tag=imported_tag,
                    imported_description=imported_description,
                )

                if conflict is None:
                    was_new = before_export is None
                    self._cross_program.import_proficy_row(
                        self._tags,
                        tag_name=imported_tag,
                        description=imported_description,
                        vessel=vessel,
                        row_data=row_data,
                    )
                    if was_new:
                        summary["new_tags_created"] += 1
                    else:
                        summary["existing_tags_updated"] += 1
                    record = self._tags[imported_tag]
                    after_export = record.proficy_export_row()
                    if was_new:
                        # Fresh import: queue only if processing changed export fields
                        # (e.g. filled missing description), not for identical spreadsheet rows.
                        self._app._queue_change_if_different(
                            vessel=vessel,
                            original_row=original_rows[row_index],
                            updated_row=after_export,
                        )
                    elif before_export is not None:
                        self._app._queue_change_if_different(
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
        finally:
            loading_merge.close()

        if pending_conflicts:
            conflict_dialog = ConflictDialog(self._window.root)
            decisions = conflict_dialog.resolve_conflicts(
                vessel=vessel,
                conflicts=[
                    {
                        "action": "skip",
                        "imported_tag": str(conflict["imported_tag"]),
                        "imported_description": str(conflict["imported_description"]),
                        "existing_tag": str(conflict["existing_tag"]),
                        "existing_description": str(conflict["existing_description"]),
                    }
                    for conflict in pending_conflicts
                ],
            )
            conflict_dialog.close()

            if decisions is None:
                debug_logger.log(
                    "conflicts",
                    "Proficy conflict resolver cancelled",
                    vessel=vessel,
                    pending_conflicts=len(pending_conflicts),
                )
                return

            loading_conflicts = LoadingDialog(
                self._window.root, title="Applying Proficy Conflict Decisions..."
            )
            loading_conflicts.show("Applying conflict decisions...")
            try:
                for decision_index, (conflict, decision) in enumerate(
                    zip(pending_conflicts, decisions), start=1
                ):
                    if decision_index == 1 or decision_index % 100 == 0:
                        loading_conflicts.update_status(
                            f"Applying decisions... {decision_index}/{len(decisions)}"
                        )
                    imported_tag = str(conflict["imported_tag"])
                    imported_description = str(conflict["imported_description"])
                    existing_tag = str(conflict["existing_tag"])
                    row_data = dict(conflict["row_data"])
                    existing_same_tag = conflict["existing_same_tag"]
                    row_index = int(conflict["row_index"])
                    original_row = original_rows[row_index]
                    action = decision.get("action", "skip")
                    if action == "skip":
                        summary["skipped_by_user"] += 1
                        continue

                    if action == "use_imported":
                        self._sync.add_or_update_imported(
                            self._tags,
                            tag_name=imported_tag,
                            description=imported_description,
                            vessel=vessel,
                            row_data=row_data,  # type: ignore[arg-type]
                        )
                        summary["resolved_use_imported"] += 1
                        if existing_same_tag is None:
                            summary["new_tags_created"] += 1
                        else:
                            summary["existing_tags_updated"] += 1
                        updated_row = dict(row_data)
                        updated_row["Name"] = imported_tag
                        updated_row["Description"] = imported_description
                        self._app._queue_change_if_different(
                            vessel=vessel,
                            original_row=original_row,
                            updated_row=updated_row,
                        )
                        self._conflicted_tags.add(imported_tag)
                        continue

                    if action == "use_existing":
                        self._sync.add_vessel_to_existing(self._tags, existing_tag, vessel)
                        summary["resolved_use_existing"] += 1
                        summary["merged_to_existing"] += 1
                        updated_row = dict(row_data)  # type: ignore[arg-type]
                        updated_row["Name"] = existing_tag
                        updated_row["Description"] = self._tags[existing_tag].description
                        self._app._queue_change_if_different(
                            vessel=vessel,
                            original_row=original_row,
                            updated_row=updated_row,
                        )
                        self._conflicted_tags.add(existing_tag)
                        continue

                    if action == "keep_both":
                        new_tag = self._sync.unique_suffix_name(self._tags, imported_tag)
                        self._sync.add_or_update_imported(
                            self._tags,
                            tag_name=new_tag,
                            description=imported_description,
                            vessel=vessel,
                            row_data=row_data,  # type: ignore[arg-type]
                        )
                        summary["resolved_keep_both"] += 1
                        summary["new_tags_created"] += 1
                        updated_row = dict(row_data)  # type: ignore[arg-type]
                        updated_row["Name"] = new_tag
                        updated_row["Description"] = imported_description
                        self._app._queue_change_if_different(
                            vessel=vessel,
                            original_row=original_row,
                            updated_row=updated_row,
                        )
                        self._conflicted_tags.add(existing_tag)
                        self._conflicted_tags.add(new_tag)
            finally:
                loading_conflicts.close()

        loading_finalize = LoadingDialog(self._window.root, title="Finalizing Import...")
        loading_finalize.show("Saving imported data...")
        try:
            self._ctx.persist_tags()
            loading_finalize.update_status("Refreshing interface...")
            self._app._refresh_filter_values()
            self._app.clear_inline_find_replace(refresh=False)
            self._app.refresh_table()
        finally:
            loading_finalize.close()
        self._notify_import_complete(summary)
        debug_logger.log(
            "import_flow",
            "Proficy import complete",
            vessel=vessel,
            total_rows=summary["total_rows"],
            conflicts_detected=summary["conflicts_detected"],
            resolved_use_imported=summary["resolved_use_imported"],
            resolved_use_existing=summary["resolved_use_existing"],
            resolved_keep_both=summary["resolved_keep_both"],
            exports_pending=self._export_queue.count(),
        )


    def _fill_missing_descriptions(
        self, rows: list[dict[str, str]], summary: dict[str, int]
    ) -> bool:
        return self._fill_missing_descriptions_for_field(
            rows=rows,
            summary=summary,
            tag_field="Name",
            description_field="Description",
            on_apply=None,
        )


    def _fill_missing_descriptions_for_field(
        self,
        *,
        rows: list[dict[str, str]],
        summary: dict[str, int],
        tag_field: str,
        description_field: str,
        on_apply: Callable[[str, str, str, int], None] | None = None,
    ) -> bool:
        used_descriptions: set[str] = {
            record.description.strip().upper()
            for record in self._tags.values()
            if record.description.strip()
        }
        for row_data in rows:
            existing_description = row_data.get(description_field, "").strip().upper()
            if existing_description:
                used_descriptions.add(existing_description)

        candidates: list[dict[str, object]] = []
        for index, row_data in enumerate(rows):
            tag_name = row_data.get(tag_field, "").strip().upper()
            description = row_data.get(description_field, "").strip().upper()
            if tag_name and not description:
                suggestion = self._suggester.suggest_unique(tag_name, used_descriptions)
                candidates.append(
                    {
                        "row_index": index,
                        "tag": tag_name,
                        "suggested": suggestion,
                    }
                )

        if not candidates:
            return True

        dialog_title = (
            "Review Missing Cimplicity Descriptions"
            if description_field == "DESC"
            else "Review Missing Descriptions"
        )
        self._window.root.update()
        edited = MissingDescriptionDialog(
            self._window.root, candidates, title=dialog_title
        ).show()
        if edited is None:
            return False

        for row_index, description in edited.items():
            if not description:
                continue
            row_data = rows[row_index]
            old_value = str(row_data.get(description_field, "")).strip().upper()
            row_data[description_field] = description
            summary["rows_missing_description_filled"] += 1
            if on_apply is not None:
                tag_name = str(row_data.get(tag_field, "")).strip().upper()
                on_apply(tag_name, old_value, description, row_index)

        return True


    def _notify_import_complete(self, summary: dict[str, int]) -> None:
        pending_rows = self._export_queue.count()
        pending_vessels = self._export_queue.vessel_count()
        pending_section = (
            f"Pending batched changes: {pending_rows}\n"
            f"Vessels with pending exports: {pending_vessels}\n\n"
            "Use the Export Changes button to write batch files."
        )

        summary_text = (
            "Import Summary\n\n"
            f"Rows read: {summary['total_rows']}\n"
            f"Rows skipped (missing Name): {summary['rows_missing_name']}\n"
            f"Rows missing description filled: {summary['rows_missing_description_filled']}\n"
            f"Unchanged matches: {summary['unchanged_matches']}\n"
            f"Conflicts detected: {summary['conflicts_detected']}\n"
            f"Conflicts skipped by user: {summary['skipped_by_user']}\n"
            f"Resolved - Use Imported: {summary['resolved_use_imported']}\n"
            f"Resolved - Use Existing: {summary['resolved_use_existing']}\n"
            f"Resolved - Keep Both: {summary['resolved_keep_both']}\n"
            f"New tags created: {summary['new_tags_created']}\n"
            f"Existing tags updated: {summary['existing_tags_updated']}\n"
            f"Merged into existing tags: {summary['merged_to_existing']}\n\n"
            f"{pending_section}"
        )
        messagebox.showinfo("Import Complete", summary_text)

