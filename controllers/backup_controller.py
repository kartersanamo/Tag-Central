"""Backup orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

from ui.backups_dialog import BackupsDialog
from ui.loading_dialog import LoadingDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class BackupController(ControllerBase):
    """Extracted from AppController — backup_controller."""

    def open_backups_page(self) -> None:
        """Opens full backup management page."""
        BackupsDialog(
            self._window.root,
            backup_service=self._backup_service,
            on_restore=self._restore_backup_from_page,
            on_revert_latest=self._revert_latest_backup_from_page,
        ).show()


    def _restore_backup_from_page(self, backup_name: str) -> bool:
        """Loads selected backup after saving temporary pre-load backup."""
        loading = LoadingDialog(self._window.root, title="Restoring Backup...")
        loading.show("Saving current state...")
        try:
            self._ctx.persist_tags()
            loading.update_status("Creating preload backup...")
            self._backup_service.create_preload_backup()
            loading.update_status(f"Restoring backup '{backup_name}'...")
            self._backup_service.restore_backup(backup_name)
            loading.update_status("Reloading restored data...")
            self._tags = self._repository.load()
            self._app._refresh_filter_values()
            self._app.refresh_table()
        finally:
            loading.close()
        return True


    def _revert_latest_backup_from_page(self) -> bool:
        """Restores the temporary pre-load backup if available."""
        loading = LoadingDialog(self._window.root, title="Reverting Backup...")
        loading.show("Restoring preload backup...")
        try:
            if not self._backup_service.restore_preload_backup():
                return False
            loading.update_status("Reloading reverted data...")
            self._tags = self._repository.load()
            self._app._refresh_filter_values()
            self._app.refresh_table()
        finally:
            loading.close()
        return True


    def _auto_backup_before_bulk(self, reason: str) -> None:
        paths = self._backup_service.create_bulk_operation_backup()
        if paths:
            self._window.status_var.set(
                f"Auto-backup ({reason}): {paths[0].name}"
            )

