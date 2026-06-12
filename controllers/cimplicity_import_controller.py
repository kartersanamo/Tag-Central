"""CimplicityImport orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

from tkinter import filedialog, messagebox, simpledialog

from app_config import BULK_DELETE_BACKUP_THRESHOLD, BULK_IMPORT_BACKUP_THRESHOLD
from services.debug_logger import debug_logger
from ui.ambiguous_address_resolver_dialog import AmbiguousAddressResolverDialog
from ui.cimplicity_link_report_dialog import CimplicityLinkReportDialog
from ui.cimplicity_manual_tasks_dialog import CimplicityManualTasksDialog
from ui.cimplicity_review_dialog import CimplicityReviewDialog
from ui.cimplicity_sync_dialog import CimplicitySyncDialog
from ui.import_dry_run_dialog import ImportDryRunDialog
from ui.loading_dialog import LoadingDialog
from ui.missing_description_dialog import MissingDescriptionDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class CimplicityImportController(ControllerBase):
    """Extracted from AppController — cimplicity_import_controller."""

    def import_cimplicity_spreadsheet(self) -> None:
        """Imports a Cimplicity Shared Name File and aligns Proficy where needed."""
        file_path = filedialog.askopenfilename(
            title="Select Cimplicity Shared Name File",
            filetypes=[("CSV Files", "*.csv")],
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

        loading = LoadingDialog(self._window.root, title="Importing Cimplicity...")
        try:
            loading.show("Loading Cimplicity CSV...")
            try:
                raw_rows = self._cimplicity_loader.load_rows(file_path)
            except Exception as error:
                loading.close()
                messagebox.showerror("Cimplicity Import Error", str(error))
                return

            loading.update_status("Checking for missing descriptions...")
            cimplicity_desc_summary: dict[str, object] = {
                "rows_missing_description_filled": 0,
                "pending_manual_tasks": [],
            }
            if not self._fill_missing_cimplicity_descriptions(
                raw_rows, vessel, cimplicity_desc_summary
            ):
                return

            loading.update_status("Normalizing imported rows...")
            prepared = self._cross_program.prepare_cimplicity_rows(raw_rows)

            loading.update_status(
                f"Analyzing sync state for {len(prepared)} rows..."
            )
            analysis = self._cross_program.analyze_cimplicity_import(
                self._tags, prepared, vessel
            )
        finally:
            loading.close()

        dry_lines = list(analysis.report_lines) + [
            "",
            f"Descriptions generated (manual tasks): "
            f"{int(cimplicity_desc_summary['rows_missing_description_filled'])}",
            f"Estimated review queue additions: {analysis.review_queue_added}",
            f"Rows needing resolver: {len(analysis.actionable)}",
            f"Rows already aligned (auto-pass): {analysis.linked_synced}",
        ]
        if not ImportDryRunDialog(
            self._window.root, "Cimplicity Import Preview", dry_lines
        ).show():
            debug_logger.log(
                "import_flow",
                "Cimplicity import cancelled at preview",
                vessel=vessel,
            )
            return

        pending_tasks = cimplicity_desc_summary.get("pending_manual_tasks", [])
        if isinstance(pending_tasks, list):
            for task in pending_tasks:
                if isinstance(task, dict):
                    self._manual_tasks.add_task(**task)
            if pending_tasks:
                self._update_manual_tasks_indicator()

        if len(prepared) >= BULK_IMPORT_BACKUP_THRESHOLD:
            self._app._auto_backup_before_bulk("cimplicity_import")

        self._last_cimplicity_link_report = list(analysis.report_lines)

        summary = {
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

        ambiguous_rows: list[dict[str, str]] = []
        dialog_rows: list[dict[str, str]] = []
        for action in analysis.actionable:
            if action.issue.startswith("ambiguous_address:"):
                candidate_tags = action.issue.split(":", 1)[1]
                ambiguous_rows.append(
                    {
                        "action": "align_selected",
                        "pt_id": action.pt_id,
                        "cimplicity_description": action.cimplicity_description,
                        "address": action.address,
                        "candidate_tags": candidate_tags,
                        "selected_tag": action.existing_tag,
                        "row_index": str(action.row_index),
                        "issue": action.issue,
                    }
                )
                continue
            dialog_rows.append(
                {
                    "action": action.default_action,
                    "pt_id": action.pt_id,
                    "cimplicity_description": action.cimplicity_description,
                    "address": action.address,
                    "existing_tag": action.existing_tag,
                    "existing_description": action.existing_description,
                    "issue": action.issue,
                    "row_index": str(action.row_index),
                    "row_data": dict(action.row_data),
                }
            )

        decisions: list[dict[str, str]] = []
        if ambiguous_rows:
            ambiguous_dialog = AmbiguousAddressResolverDialog(self._window.root)
            ambiguous_result = ambiguous_dialog.resolve_rows(
                vessel=vessel, rows=ambiguous_rows
            )
            ambiguous_dialog.close()
            if ambiguous_result is None:
                debug_logger.log(
                    "import_flow",
                    "Ambiguous address resolver cancelled",
                    vessel=vessel,
                    ambiguous_rows=len(ambiguous_rows),
                )
                return

            loading_ambiguous = LoadingDialog(
                self._window.root,
                title="Resolving Ambiguous Address Matches...",
            )
            loading_ambiguous.show("Applying ambiguous match resolutions...")
            try:
                for index, row in enumerate(ambiguous_result, start=1):
                    if index == 1 or index % 20 == 0:
                        loading_ambiguous.update_status(
                            f"Resolving ambiguous rows... {index}/{len(ambiguous_result)}"
                        )
                    row_index = int(row.get("row_index", "-1"))
                    pt_id = str(row.get("pt_id", "")).strip().upper()
                    selected_tag = str(row.get("selected_tag", "")).strip().upper()
                    raw_candidates = str(row.get("candidate_tags", ""))
                    candidates = [
                        item.strip().upper()
                        for item in raw_candidates.split(",")
                        if item.strip()
                    ]
                    if selected_tag not in candidates and candidates:
                        selected_tag = candidates[0]
                    action_name = str(row.get("action", "skip")).strip().lower()
                    base_action = "skip"
                    if action_name in {"align_selected", "merge_then_align"}:
                        base_action = "align_proficy"
                    elif action_name == "link_only_selected":
                        base_action = "link_only"
                    elif action_name == "flag_manual_cimplicity":
                        base_action = "flag_manual_cimplicity"

                    if (
                        action_name == "merge_then_align"
                        and selected_tag
                        and selected_tag in self._tags
                    ):
                        for candidate in candidates:
                            if candidate == selected_tag:
                                continue
                            if candidate not in self._tags:
                                continue
                            try:
                                merged = self._merge_service.merge_tags(
                                    self._tags, selected_tag, candidate
                                )
                            except KeyError:
                                continue
                            export_row = merged.proficy_export_row()
                            for tag_vessel in merged.vessels or {"GLOBAL"}:
                                self._app._queue_change(tag_vessel, export_row)
                            debug_logger.log(
                                "conflicts",
                                "Merged ambiguous address duplicate",
                                selected_tag=selected_tag,
                                removed_tag=candidate,
                                pt_id=pt_id,
                            )

                    decisions.append(
                        {
                            "action": base_action,
                            "pt_id": pt_id,
                            "row_index": str(row_index),
                            "existing_tag": selected_tag,
                            "issue": str(row.get("issue", "")),
                        }
                    )
            finally:
                loading_ambiguous.close()

        if dialog_rows:
            sync_dialog = CimplicitySyncDialog(self._window.root)
            result = sync_dialog.resolve_rows(vessel=vessel, rows=dialog_rows)
            sync_dialog.close()
            if result is None:
                debug_logger.log(
                    "import_flow",
                    "Cimplicity sync resolver cancelled",
                    vessel=vessel,
                    actionable_rows=len(dialog_rows),
                )
                return
            decisions.extend(result)

        loading_apply = LoadingDialog(self._window.root, title="Applying Cimplicity Sync...")
        loading_apply.show("Applying your sync decisions...")
        try:
            row_by_index = {row.row_index: row for row in prepared}
            row_by_pt_id = {row.pt_id: row for row in prepared}
            for decision_index, decision in enumerate(decisions, start=1):
                if decision_index == 1 or decision_index % 25 == 0:
                    loading_apply.update_status(
                        f"Applying decisions... {decision_index}/{len(decisions)}"
                    )
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
                link = self._cross_program._linker.link_cimplicity_row(
                    self._tags, row.pt_id, row.address
                )
                canonical_tag = self._cross_program.resolve_tag_key(
                    self._tags, row, link, preferred_key=stale_tag or None
                )
                if canonical_tag is None and action not in {"skip", "flag_manual_cimplicity"}:
                    summary["skipped"] += 1
                    continue

                changed, export_row = self._cross_program.apply_cimplicity_row(
                    self._tags,
                    row,
                    vessel,
                    action,
                    canonical_tag=canonical_tag,
                )
                if action == "flag_manual_cimplicity":
                    summary["manual_cimplicity_flags"] += 1
                    self._cimplicity_manual_entries.append(
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
                        self._app._queue_change(vessel=vessel, row_data=export_row)
                        summary["proficy_exports_queued"] += 1
                elif action == "link_only" and changed:
                    summary["linked_synced"] += 1

            for row_index, row in enumerate(prepared, start=1):
                if row_index == 1 or row_index % 200 == 0:
                    loading_apply.update_status(
                        f"Auto-aligning matched rows... {row_index}/{len(prepared)}"
                    )
                if any(int(d.get("row_index", -1)) == row.row_index for d in decisions):
                    continue
                link = self._cross_program._linker.link_cimplicity_row(
                    self._tags, row.pt_id, row.address
                )
                if link.canonical_tag and not self._cross_program._detect_issues(
                    self._tags[link.canonical_tag], row
                ):
                    _, export_row = self._cross_program.apply_cimplicity_row(
                        self._tags,
                        row,
                        vessel,
                        "align_proficy",
                        canonical_tag=link.canonical_tag,
                    )
                    summary["auto_aligned"] += 1
                    if export_row:
                        self._app._queue_change(vessel=vessel, row_data=export_row)
                        summary["proficy_exports_queued"] += 1

            from datetime import datetime, timezone

            from services.cimplicity_review_queue import ReviewQueueItem

            for row_index, row in enumerate(prepared, start=1):
                if row_index == 1 or row_index % 200 == 0:
                    loading_apply.update_status(
                        f"Updating review queue... {row_index}/{len(prepared)}"
                    )
                link = self._cross_program._linker.link_cimplicity_row(
                    self._tags, row.pt_id, row.address
                )
                if link.canonical_tag or link.ambiguous_tags:
                    continue
                self._cross_program.review_queue.add(
                    ReviewQueueItem(
                        vessel=vessel,
                        pt_id=row.pt_id,
                        description=row.description,
                        address=row.address,
                        row_data=row.row_data,
                        imported_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

            loading_apply.update_status("Saving database and refreshing UI...")
            self._ctx.persist_tags()
            self._app._refresh_filter_values()
            self._update_review_queue_indicator()
            self._update_manual_tasks_indicator()
            self._app.clear_inline_find_replace(refresh=False)
            self._app.refresh_table()
        finally:
            loading_apply.close()

        self._notify_cimplicity_import_complete(summary)
        debug_logger.log(
            "import_flow",
            "Cimplicity import complete",
            vessel=vessel,
            total_rows=summary["total_rows"],
            linked_synced=summary["linked_synced"],
            auto_aligned=summary["auto_aligned"],
            skipped=summary["skipped"],
            review_queue_added=summary["review_queue_added"],
            manual_flags=summary["manual_cimplicity_flags"],
            descriptions_filled=summary["rows_missing_description_filled"],
            exports_pending=self._export_queue.count(),
        )


    def import_spreadsheet(self) -> None:
        """Backward-compatible alias for Proficy import."""
        self._app.import_proficy_spreadsheet()


    def _notify_cimplicity_import_complete(self, summary: dict[str, int]) -> None:
        apply_lines = [
            f"Descriptions generated (Cimplicity manual tasks): "
            f"{summary.get('rows_missing_description_filled', 0)}",
            f"Aligned Proficy to Cimplicity: {summary['auto_aligned']}",
            f"Linked only (still needs align): {summary['linked_synced']}",
            f"Sent to review queue: {summary['review_queue_added']}",
            f"Skipped: {summary['skipped']}",
            f"Proficy exports queued: {summary['proficy_exports_queued']}",
            f"Manual Cimplicity flags: {summary['manual_cimplicity_flags']}",
        ]
        CimplicityLinkReportDialog(
            self._window.root,
            self._last_cimplicity_link_report,
            apply_lines,
        )
        messagebox.showinfo(
            "Cimplicity Import Complete",
            f"Processed {summary['total_rows']} Cimplicity row(s). "
            "See the link report for details.",
        )
        if self._cimplicity_manual_entries:
            path = self._cimplicity_report.write_report(
                "GLOBAL", self._cimplicity_manual_entries
            )
            if path:
                messagebox.showinfo(
                    "Cimplicity Manual Report",
                    f"Manual Cimplicity work list written to:\n{path}",
                )
                self._cimplicity_manual_entries.clear()


    def _fill_missing_cimplicity_descriptions(
        self,
        rows: list[dict[str, str]],
        vessel: str,
        summary: dict[str, object],
    ) -> bool:
        pending_tasks = summary.setdefault("pending_manual_tasks", [])
        if not isinstance(pending_tasks, list):
            summary["pending_manual_tasks"] = pending_tasks = []

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
        ok = self._app._fill_missing_descriptions_for_field(
            rows=rows,
            summary=fill_summary,
            tag_field="PT_ID",
            description_field="DESC",
            on_apply=queue_manual_task,
        )
        summary["rows_missing_description_filled"] = fill_summary[
            "rows_missing_description_filled"
        ]
        return ok


    def open_cimplicity_review(self) -> None:
        CimplicityReviewDialog(
            self._window.root,
            review_queue=self._cross_program.review_queue,
            on_create_proficy=self._create_proficy_from_review_items,
            on_dismiss=self._dismiss_review_items,
        )


    def open_cimplicity_tasks(self) -> None:
        CimplicityManualTasksDialog(
            self._window.root,
            tasks=self._manual_tasks,
            on_change=self._update_manual_tasks_indicator,
        )


    def _create_proficy_from_review_items(self, items: list) -> None:
        from services.cimplicity_review_queue import ReviewQueueItem

        queue_items = [item for item in items if isinstance(item, ReviewQueueItem)]
        if not queue_items:
            return

        if len(queue_items) >= BULK_DELETE_BACKUP_THRESHOLD:
            self._app._auto_backup_before_bulk("cimplicity_review_create")

        loading = LoadingDialog(self._window.root, title="Creating Proficy Tags...")
        loading.show(f"Creating {len(queue_items)} Proficy tag(s)...")
        try:
            created, skipped = self._apply_create_proficy_from_review_items(
                queue_items, loading=loading
            )
        finally:
            loading.close()

        if created == 0 and skipped == 0:
            return
        summary = f"Created {created} Proficy tag(s) and queued them for export."
        if skipped:
            summary += f"\nSkipped {skipped} item(s) that already exist as tags."
        messagebox.showinfo("Proficy Tags Created", summary)


    def _apply_create_proficy_from_review_items(
        self,
        items: list,
        *,
        loading: LoadingDialog | None = None,
    ) -> tuple[int, int]:
        keys = [(item.vessel, item.pt_id) for item in items]
        result = self._app._core.cimplicity_review_create_proficy(keys)
        self._update_review_queue_indicator()
        self._app._update_pending_change_indicator()
        self._app._refresh_filter_values()
        self._app.refresh_table()
        return result["created"], result["skipped"]


    def _dismiss_review_items(self, items: list) -> None:
        from services.cimplicity_review_queue import ReviewQueueItem

        queue_items = [item for item in items if isinstance(item, ReviewQueueItem)]
        if not queue_items:
            return

        keys = [(item.vessel, item.pt_id) for item in queue_items]
        self._app._core.cimplicity_review_dismiss(keys)
        self._update_review_queue_indicator()


    def _update_review_queue_indicator(self) -> None:
        self._window.set_review_queue_count(self._cross_program.review_queue.count())


    def _update_manual_tasks_indicator(self) -> None:
        self._window.set_manual_tasks_count(self._manual_tasks.pending_count())


    def _resolve_pending_cimplicity_tasks_on_close(self) -> bool:
        """Returns True when there are no pending manual Cimplicity tasks left."""
        if self._manual_tasks.pending_count() == 0:
            return True

        pending_count = self._manual_tasks.pending_count()
        close_choice = messagebox.askyesnocancel(
            "Pending Cimplicity Tasks",
            f"There are {pending_count} pending manual Cimplicity task(s).\n\n"
            "Select Yes to open the Cimplicity tasks list now.\n"
            "Select No to discard all pending Cimplicity tasks.\n"
            "Select Cancel to go back to the application.",
        )
        if close_choice is None:
            return False

        if close_choice:
            dialog = CimplicityManualTasksDialog(
                self._window.root,
                tasks=self._manual_tasks,
                on_change=self._update_manual_tasks_indicator,
            )
            dialog.show_modal()
            if self._manual_tasks.pending_count() > 0:
                return False
            return True

        confirm_abort = messagebox.askyesno(
            "Abort Pending Cimplicity Tasks",
            "Abort and discard all pending manual Cimplicity tasks?\n\n"
            "This cannot be undone.",
        )
        if confirm_abort:
            self._manual_tasks.clear_all()
            self._update_manual_tasks_indicator()
            return True
        return False

