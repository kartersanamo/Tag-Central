"""Thin application facade coordinating sub-controllers."""

from __future__ import annotations

from collections.abc import Callable
import sys

import tkinter as tk

from controllers.app_context import AppContext
from controllers.backup_controller import BackupController
from controllers.cimplicity_import_controller import CimplicityImportController
from controllers.documentation_controller import DocumentationController
from controllers.export_controller import ExportController
from controllers.proficy_import_controller import ProficyImportController
from controllers.tag_mutation_controller import TagMutationController
from controllers.tag_table_controller import TagTableController
from services.export_queue_service import export_fields_for_compare
from services.find_replace_service import (
    format_find_replace_display,
    highlight_find_text,
    matches_find_scope,
)
from tkinter import messagebox

from ui.cimplicity_manual_tasks_dialog import CimplicityManualTasksDialog
from ui.main_window import MainWindow


class AppController:
    """Coordinates UI, persistence, import logic, and exports."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        startup_status: Callable[[str], None] | None = None,
        skip_initial_refresh: bool = False,
    ) -> None:
        def status(message: str) -> None:
            if startup_status is not None:
                startup_status(message)

        status("Loading database…")
        self._ctx = AppContext(root=root)

        from core.tag_central_app import TagCentralApp

        self._core = TagCentralApp.from_context(self._ctx)

        self._table = TagTableController(self._ctx, self)
        self._export = ExportController(self._ctx, self)
        self._backup = BackupController(self._ctx, self)
        self._mutation = TagMutationController(self._ctx, self)
        self._proficy = ProficyImportController(self._ctx, self)
        self._cimplicity = CimplicityImportController(self._ctx, self)
        self._documentation = DocumentationController(self._ctx, self)

        status("Building interface…")
        self._ctx.window = MainWindow(root)
        self._bind_events()
        self._table._refresh_filter_values()
        status("Analyzing tags…")
        self._table._recalculate_conflicted_tags()
        self._window.set_pending_change_count(0)
        self._cimplicity._update_review_queue_indicator()
        self._cimplicity._update_manual_tasks_indicator()
        self._window.root.protocol("WM_DELETE_WINDOW", self._handle_app_close)
        if not skip_initial_refresh:
            tag_count = len(self._tags)
            status(f"Loading {tag_count} tag{'s' if tag_count != 1 else ''}…")
            self.refresh_table()

    @property
    def _tags(self):
        return self._ctx.tags

    @property
    def _window(self):
        return self._ctx.window

    @property
    def _column_heading_labels(self):
        return self._ctx.column_heading_labels

    def finish_startup(self, startup_status: Callable[[str], None] | None = None) -> None:
        """Populates the tag table after the main window is visible."""
        if startup_status is not None:
            tag_count = len(self._tags)
            startup_status(
                f"Loading {tag_count} tag{'s' if tag_count != 1 else ''}…"
            )
        self.refresh_table()

    def _bind_events(self) -> None:
        assert self._window.import_proficy_button and self._window.import_cimplicity_button
        assert self._window.cimplicity_review_button and self._window.cimplicity_tasks_button
        assert self._window.program_filter_combo
        assert self._window.import_button and self._window.backups_button
        assert self._window.refresh_button and self._window.reset_filter_button
        assert self._window.add_tag_button
        assert self._window.find_replace_button
        assert (
            self._window.find_replace_apply_button
            and self._window.find_replace_delete_button
            and self._window.find_replace_clear_button
        )
        assert self._window.find_scope_combo
        assert self._window.export_changes_button
        assert self._window.documentation_button
        assert self._window.review_export_queue_button
        assert self._window.change_tag_button and self._window.vessel_combo
        assert self._window.array_expand_toggle_button
        assert self._window.tree and self._window.context_menu

        self._window.import_proficy_button.configure(command=self.import_proficy_spreadsheet)
        self._window.import_cimplicity_button.configure(command=self.import_cimplicity_spreadsheet)
        self._window.cimplicity_review_button.configure(command=self.open_cimplicity_review)
        self._window.cimplicity_tasks_button.configure(command=self.open_cimplicity_tasks)
        self._window.import_button.configure(command=self.import_proficy_spreadsheet)
        self._window.backups_button.configure(command=self.open_backups_page)
        self._window.documentation_button.configure(command=self.generate_documentation)
        self._window.refresh_button.configure(command=self.refresh_from_disk)
        self._window.add_tag_button.configure(command=self.add_new_tag)
        self._window.find_replace_button.configure(
            command=self._window.toggle_find_replace_visibility
        )
        self._window.find_replace_apply_button.configure(command=self.apply_inline_find_replace)
        self._window.find_replace_delete_button.configure(
            command=self.delete_inline_find_matches
        )
        self._window.find_replace_clear_button.configure(command=self.clear_inline_find_replace)
        self._window.export_changes_button.configure(command=self.export_pending_changes)
        self._window.review_export_queue_button.configure(
            command=self.open_export_queue_inspector
        )
        self._window.reset_filter_button.configure(command=self.reset_vessel_filter)
        self._window.change_tag_button.configure(command=self.edit_selected_tag)
        self._window.array_expand_toggle_button.configure(
            command=self.toggle_all_array_indices
        )

        self._window.search_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.find_text_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.replace_text_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.find_scope_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.preview_changes_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.view_conflicts_var.trace_add(
            "write", lambda *_: self._on_view_conflicts_toggle()
        )
        self._window.vessel_combo.bind("<<ComboboxSelected>>", self.apply_vessel_filter)
        self._window.program_filter_combo.bind(
            "<<ComboboxSelected>>", lambda *_: self.refresh_table()
        )
        self._window.tree.bind("<Button-3>", self._show_context_menu)
        self._window.tree.bind("<Double-1>", self._on_tree_double_click)
        for copy_binding in ("<Control-c>", "<Control-C>"):
            self._window.tree.bind(copy_binding, self._on_copy_tags_shortcut)
        if sys.platform == "darwin":
            for copy_binding in ("<Command-c>", "<Command-C>"):
                self._window.tree.bind(copy_binding, self._on_copy_tags_shortcut)
        for column_name in self._column_heading_labels:
            self._window.tree.heading(
                column_name,
                command=lambda value=column_name: self._on_tree_heading_click(value),
            )
        self._window.context_menu.entryconfigure(0, command=self.edit_selected_tag)
        self._window.context_menu.entryconfigure(1, command=self.copy_selected_tags)
        self._window.context_menu.entryconfigure(
            2, command=self.align_selected_to_cimplicity
        )
        self._window.context_menu.entryconfigure(
            3, command=self.toggle_selected_array_indices
        )
        self._window.context_menu.entryconfigure(
            4, command=self.jump_to_selected_mismatches
        )
        self._window.context_menu.entryconfigure(5, command=self.view_selected_tag_diff)
        self._window.context_menu.entryconfigure(
            6, command=self.increment_selected_descriptions
        )
        self._window.context_menu.entryconfigure(8, command=self.merge_selected_tags)
        self._window.context_menu.entryconfigure(10, command=self.add_new_tag)
        self._window.context_menu.entryconfigure(12, command=self.delete_selected_tags)
        self._table._refresh_tree_heading_sort_markers()

    def _handle_app_close(self) -> None:
        """Prevents closing while Proficy exports or Cimplicity manual tasks are pending."""
        if self._export._export_queue.count() and not self._export._resolve_pending_exports_on_close():
            return
        if self._cimplicity._manual_tasks.pending_count() and not self._cimplicity._resolve_pending_cimplicity_tasks_on_close():
            return
        self._window.root.destroy()

    # --- Static helpers preserved for tests ---

    @staticmethod
    def _matches_find_scope(*args, **kwargs):
        return matches_find_scope(*args, **kwargs)

    @staticmethod
    def _highlight_find_text(*args, **kwargs):
        return highlight_find_text(*args, **kwargs)

    @staticmethod
    def _format_find_replace_display(*args, **kwargs):
        return format_find_replace_display(*args, **kwargs)

    @staticmethod
    def _export_fields_for_compare(row: dict[str, str]) -> dict[str, str]:
        return export_fields_for_compare(row)

    # --- Table ---

    def refresh_table(self) -> None:
        return self._table.refresh_table()

    def refresh_from_disk(self) -> None:
        return self._table.refresh_from_disk()

    def apply_vessel_filter(self, event: tk.Event | None = None) -> None:
        return self._table.apply_vessel_filter(event)

    def reset_vessel_filter(self) -> None:
        return self._table.reset_vessel_filter()

    def apply_inline_find_replace(self) -> None:
        return self._table.apply_inline_find_replace()

    def clear_inline_find_replace(self, refresh: bool = True) -> None:
        return self._table.clear_inline_find_replace(refresh)

    def delete_inline_find_matches(self) -> None:
        return self._table.delete_inline_find_matches()

    def copy_selected_tags(self) -> None:
        return self._table.copy_selected_tags()

    def jump_to_selected_mismatches(self) -> None:
        return self._table.jump_to_selected_mismatches()

    def toggle_selected_array_indices(self) -> None:
        return self._table.toggle_selected_array_indices()

    def toggle_all_array_indices(self) -> None:
        return self._table.toggle_all_array_indices()

    def _on_tree_heading_click(self, column_name: str) -> None:
        return self._table._on_tree_heading_click(column_name)

    def _show_context_menu(self, event: tk.Event) -> None:
        return self._table._show_context_menu(event)

    def _on_tree_double_click(self, event: tk.Event) -> None:
        return self._table._on_tree_double_click(event)

    def _on_copy_tags_shortcut(self, event: tk.Event) -> str:
        return self._table._on_copy_tags_shortcut(event)

    def _on_view_conflicts_toggle(self) -> None:
        return self._table._on_view_conflicts_toggle()

    def _refresh_filter_values(self) -> None:
        return self._table._refresh_filter_values()

    def _recalculate_conflicted_tags(self) -> None:
        return self._table._recalculate_conflicted_tags()

    def _get_selected_tag_names(self) -> list[str]:
        return self._table._get_selected_tag_names()

    def _can_increment_descriptions(self, tag_names: list[str]) -> bool:
        return self._mutation._can_increment_descriptions(tag_names)

    # --- Export ---

    def open_export_queue_inspector(self) -> None:
        return self._export.open_export_queue_inspector()

    def export_pending_changes(self) -> bool:
        return self._export.export_pending_changes()

    def _queue_change(self, *args, **kwargs) -> None:
        return self._export._queue_change(*args, **kwargs)

    def _queue_change_if_different(self, *args, **kwargs) -> None:
        return self._export._queue_change_if_different(*args, **kwargs)

    def _update_pending_change_indicator(self) -> None:
        return self._export._update_pending_change_indicator()

    # --- Backup ---

    def open_backups_page(self) -> None:
        return self._backup.open_backups_page()

    def _auto_backup_before_bulk(self, reason: str) -> None:
        return self._backup._auto_backup_before_bulk(reason)

    # --- Tag mutation ---

    def edit_selected_tag(self) -> None:
        return self._mutation.edit_selected_tag()

    def add_new_tag(self) -> None:
        return self._mutation.add_new_tag()

    def delete_selected_tags(self) -> None:
        return self._mutation.delete_selected_tags()

    def merge_selected_tags(self) -> None:
        return self._mutation.merge_selected_tags()

    def view_selected_tag_diff(self) -> None:
        return self._mutation.view_selected_tag_diff()

    def align_selected_to_cimplicity(self) -> None:
        return self._mutation.align_selected_to_cimplicity()

    def increment_selected_descriptions(self) -> None:
        return self._mutation.increment_selected_descriptions()

    # --- Proficy import ---

    def import_proficy_spreadsheet(self) -> None:
        return self._proficy.import_proficy_spreadsheet()

    def import_spreadsheet(self) -> None:
        return self._cimplicity.import_spreadsheet()

    def _fill_missing_descriptions_for_field(self, *args, **kwargs) -> bool:
        return self._proficy._fill_missing_descriptions_for_field(*args, **kwargs)

    # --- Cimplicity import ---

    def import_cimplicity_spreadsheet(self) -> None:
        return self._cimplicity.import_cimplicity_spreadsheet()

    def open_cimplicity_review(self) -> None:
        return self._cimplicity.open_cimplicity_review()

    def open_cimplicity_tasks(self) -> None:
        return self._cimplicity.open_cimplicity_tasks()

    def _update_review_queue_indicator(self) -> None:
        return self._cimplicity._update_review_queue_indicator()

    def _update_manual_tasks_indicator(self) -> None:
        return self._cimplicity._update_manual_tasks_indicator()

    # --- Documentation ---

    def generate_documentation(self) -> None:
        return self._documentation.generate_documentation()

    def _reveal_path(self, path) -> None:
        return self._documentation._reveal_path(path)
