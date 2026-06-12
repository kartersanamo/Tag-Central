"""Export orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

from tkinter import messagebox

from app_config import EXPORT_FOLDER
from services.debug_logger import debug_logger
from services.export_queue_service import export_fields_for_compare
from ui.export_queue_dialog import ExportQueueDialog
from ui.export_validation_dialog import ExportValidationDialog
from ui.loading_dialog import LoadingDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class ExportController(ControllerBase):
    """Extracted from AppController — export_controller."""

    def open_export_queue_inspector(self) -> None:
        ExportQueueDialog(
            self._window.root,
            self._export_queue,
            on_change=self._update_pending_change_indicator,
        )


    def _update_pending_change_indicator(self) -> None:
        self._window.set_pending_change_count(self._export_queue.count())


    def _queue_change(
        self,
        vessel: str,
        row_data: dict[str, str],
        baseline: dict[str, str] | None = None,
    ) -> None:
        self._export_queue.add(vessel, row_data, baseline=baseline)
        debug_logger.log(
            "export_queue",
            "Queued export row",
            vessel=vessel,
            name=row_data.get("Name", ""),
            description=row_data.get("Description", ""),
            address=row_data.get("IOAddress", row_data.get("Address", "")),
        )
        self._update_pending_change_indicator()


    def _queue_change_if_different(
        self,
        vessel: str,
        original_row: dict[str, str],
        updated_row: dict[str, str],
    ) -> None:
        """Queues export only when Name, Description, or address actually changed."""
        if self._export_queue.add_if_different(vessel, original_row, updated_row):
            self._update_pending_change_indicator()


    def _export_fields_for_compare(row: dict[str, str]) -> dict[str, str]:
        """Extracts export-relevant fields so extra Proficy columns do not false-queue."""
        from services.export_queue_service import export_fields_for_compare

        return export_fields_for_compare(row)


    def export_pending_changes(self) -> bool:
        """Writes all pending vessel batches to export files."""
        root = self._window.root
        if self._export_queue.count() == 0:
            messagebox.showinfo(
                "No Pending Changes",
                "There are no pending changes to export.",
                parent=root,
            )
            return True
        debug_logger.log(
            "export_queue",
            "Starting export pending changes",
            pending_count=self._export_queue.count(),
            vessel_count=self._export_queue.vessel_count(),
        )

        snapshot = self._export_queue.all_entries()
        exports = self._export_queue.to_legacy_exports()
        loading_export = LoadingDialog(root, title="Exporting Changes...")
        loading_export.show("Writing export batch files...")
        written_paths: list = []
        pending_count = len(snapshot)
        try:
            written_paths = self._export_service.write_exports(exports)
            if not written_paths:
                raise RuntimeError(
                    "No export files were written. Check that the export folder exists "
                    f"and is writable:\n{EXPORT_FOLDER}"
                )
            self._export_queue.clear()
            self._update_pending_change_indicator()
        except Exception as error:
            messagebox.showerror(
                "Export Failed",
                f"Could not write Proficy export files.\n\n{error}\n\n"
                f"Export folder:\n{EXPORT_FOLDER}",
                parent=root,
            )
            debug_logger.log(
                "export_queue",
                "Export failed",
                error=str(error),
                export_folder=str(EXPORT_FOLDER),
            )
            return False
        finally:
            loading_export.close()

        rendered_paths = "\n".join(str(path) for path in written_paths)
        messagebox.showinfo(
            "Changes Exported",
            f"Exported {pending_count} change(s).\n\nFiles:\n{rendered_paths}\n\n"
            f"Folder:\n{EXPORT_FOLDER}",
            parent=root,
        )
        self._reveal_export_folder()
        if messagebox.askyesno(
            "Validate Export",
            "Validate the exported CSV files against the queued changes?",
            parent=root,
        ):
            self._validate_export_files(written_paths, snapshot)
        debug_logger.log(
            "export_queue",
            "Finished export pending changes",
            exported_rows=pending_count,
            files=[str(path) for path in written_paths],
        )
        return True


    def _reveal_export_folder(self) -> None:
        """Opens the export folder in Finder / Explorer when possible."""
        EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        self._app._reveal_path(EXPORT_FOLDER)


    def _validate_export_files(
        self,
        paths: list,
        expected_entries: list,
    ) -> None:
        from models.pending_export import PendingExportChange

        by_vessel: dict[str, list[dict[str, str]]] = {}
        for entry in expected_entries:
            assert isinstance(entry, PendingExportChange)
            by_vessel.setdefault(entry.vessel, []).append(dict(entry.row_data))

        results = []
        for path in paths:
            vessel_key = str(path.name).split("_BATCH_EXPORT")[0]
            expected_rows = by_vessel.get(vessel_key, [])
            results.append(
                self._export_validator.validate_export_file(path, expected_rows)
            )
        ExportValidationDialog(self._window.root, results)


    def _resolve_pending_exports_on_close(self) -> bool:
        """Returns True when there are no pending Proficy export batches left."""
        if self._export_queue.count() == 0:
            return True

        close_choice = messagebox.askyesnocancel(
            "Pending Changes",
            "There are pending batched changes.\n\n"
            "Select Yes to export changes now.\n"
            "Select No to abort all pending changes.\n"
            "Select Cancel to go back to the application.",
        )
        if close_choice is None:
            return False

        if close_choice:
            self.export_pending_changes()
            return self._export_queue.count() == 0

        confirm_abort = messagebox.askyesno(
            "Abort Pending Changes",
            "Abort and discard all pending batched changes?\n\nThis cannot be undone.",
        )
        if confirm_abort:
            self._export_queue.clear()
            self._update_pending_change_indicator()
            return True
        return False

