"""Application orchestration and event handlers."""

import tkinter as tk
import re
from tkinter import filedialog, messagebox, simpledialog

from app_config import (
    BACKUP_FOLDER,
    CONFLICT_GROUP_COLORS,
    DATABASE_FILE,
    EXPORT_FOLDER,
    SYNC_STATUS_LABELS,
)
from models.tag_record import (
    SYNC_NEEDS_ALIGN,
    SYNC_PROFICY_DRIFT,
    SYNC_PROFICY_ONLY,
    SYNC_SYNCED,
    TagRecord,
)
from services.backup_service import BackupService
from services.cimplicity_change_report import CimplicityChangeReport
from services.cimplicity_loader import CimplicityLoader
from services.cross_program_sync_service import (
    CimplicityImportRow,
    CimplicitySyncAction,
    CrossProgramSyncService,
    normalize_description,
)
from services.description_suggester import DescriptionSuggester
from services.export_service import ExportService
from services.spreadsheet_loader import SpreadsheetLoader
from services.tag_repository import TagRepository
from services.tag_sync_service import TagSyncService
from ui.backups_dialog import BackupsDialog
from ui.add_tag_dialog import AddTagDialog
from ui.cimplicity_review_dialog import CimplicityReviewDialog
from ui.cimplicity_sync_dialog import CimplicitySyncDialog
from ui.conflict_dialog import ConflictDialog
from ui.edit_tag_dialog import EditTagDialog
from ui.loading_dialog import LoadingDialog
from ui.main_window import MainWindow
from ui.missing_description_dialog import MissingDescriptionDialog


class AppController:
    """Coordinates UI, persistence, import logic, and exports."""

    def __init__(self, root: tk.Tk) -> None:
        self._repository = TagRepository(DATABASE_FILE)
        self._loader = SpreadsheetLoader()
        self._cimplicity_loader = CimplicityLoader()
        self._suggester = DescriptionSuggester()
        self._export_service = ExportService(EXPORT_FOLDER)
        self._backup_service = BackupService(BACKUP_FOLDER, DATABASE_FILE)
        self._sync = TagSyncService()
        self._cross_program = CrossProgramSyncService()
        self._cimplicity_report = CimplicityChangeReport()
        self._cimplicity_manual_entries: list[dict[str, str]] = []
        self._tags: dict[str, TagRecord] = self._repository.load()
        self._active_vessel_filter: str | None = None
        self._conflicted_tags: set[str] = set()
        self._tag_conflict_peers: dict[str, list[str]] = {}
        self._tag_conflict_group: dict[str, int] = {}
        self._view_conflict_session_tags: set[str] = set()
        self._pending_changes: dict[str, list[dict[str, object]]] = {}
        self._sort_column = "tag_name"
        self._sort_descending = False
        self._column_heading_labels = {
            "row_number": "#",
            "tag_name": "Tag",
            "proficy_name": "Proficy Name",
            "cimplicity_pt_id": "Cimplicity PT_ID",
            "description": "Description",
            "address": "Address",
            "sync_status": "Sync",
            "conflict_group": "Group",
            "conflicts_with": "Conflicts With",
            "vessels": "Vessels",
        }

        self._window = MainWindow(root)
        self._bind_events()
        self._refresh_filter_values()
        self._recalculate_conflicted_tags()
        self._window.set_pending_change_count(0)
        self._update_review_queue_indicator()
        self._window.root.protocol("WM_DELETE_WINDOW", self._handle_app_close)
        self.refresh_table()

    def _bind_events(self) -> None:
        assert self._window.import_proficy_button and self._window.import_cimplicity_button
        assert self._window.align_selected_button and self._window.cimplicity_review_button
        assert self._window.program_filter_combo
        assert self._window.import_button and self._window.backups_button
        assert self._window.refresh_button and self._window.reset_filter_button
        assert self._window.add_tag_button
        assert self._window.find_replace_button
        assert self._window.find_replace_apply_button and self._window.find_replace_clear_button
        assert self._window.find_scope_combo
        assert self._window.export_changes_button
        assert self._window.change_tag_button and self._window.vessel_combo
        assert self._window.tree and self._window.context_menu

        self._window.import_proficy_button.configure(command=self.import_proficy_spreadsheet)
        self._window.import_cimplicity_button.configure(command=self.import_cimplicity_spreadsheet)
        self._window.align_selected_button.configure(command=self.align_selected_to_cimplicity)
        self._window.cimplicity_review_button.configure(command=self.open_cimplicity_review)
        self._window.import_button.configure(command=self.import_proficy_spreadsheet)
        self._window.backups_button.configure(command=self.open_backups_page)
        self._window.refresh_button.configure(command=self.refresh_from_disk)
        self._window.add_tag_button.configure(command=self.add_new_tag)
        self._window.find_replace_button.configure(
            command=self._window.toggle_find_replace_visibility
        )
        self._window.find_replace_apply_button.configure(command=self.apply_inline_find_replace)
        self._window.find_replace_clear_button.configure(command=self.clear_inline_find_replace)
        self._window.export_changes_button.configure(command=self.export_pending_changes)
        self._window.reset_filter_button.configure(command=self.reset_vessel_filter)
        self._window.change_tag_button.configure(command=self.edit_selected_tag)

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
        for column_name in self._column_heading_labels:
            self._window.tree.heading(
                column_name,
                command=lambda value=column_name: self._on_tree_heading_click(value),
            )
        self._window.context_menu.entryconfigure(0, command=self.edit_selected_tag)
        self._window.context_menu.entryconfigure(
            1, command=self.align_selected_to_cimplicity
        )
        self._window.context_menu.entryconfigure(3, command=self.add_new_tag)
        self._window.context_menu.entryconfigure(5, command=self.delete_selected_tags)
        self._refresh_tree_heading_sort_markers()

    def _on_tree_heading_click(self, column_name: str) -> None:
        """Sorts table by selected column and toggles direction on repeat click."""
        if self._sort_column == column_name:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = column_name
            self._sort_descending = False
        self.refresh_table()

    def _refresh_tree_heading_sort_markers(self) -> None:
        """Shows active sort column and direction in header labels."""
        assert self._window.tree
        arrow = " ▼" if self._sort_descending else " ▲"
        for column_name, label in self._column_heading_labels.items():
            suffix = arrow if column_name == self._sort_column else ""
            self._window.tree.heading(column_name, text=f"{label}{suffix}")

    def _sort_rows(self, rows_to_show: list[tuple[str, TagRecord]]) -> None:
        """Sorts visible rows by active header column."""

        def sort_key(item: tuple[str, TagRecord]) -> tuple[object, str]:
            tag_name, record = item
            group_id = self._tag_conflict_group.get(tag_name)
            peers = self._tag_conflict_peers.get(tag_name, [])

            value_map: dict[str, object] = {
                "row_number": tag_name,
                "tag_name": record.tag_name,
                "proficy_name": record.proficy_name or "",
                "cimplicity_pt_id": record.cimplicity_pt_id or "",
                "description": record.description,
                "address": self._record_address(record),
                "sync_status": self._sync_status_label(record.sync_status),
                "conflict_group": group_id if group_id is not None else 999999,
                "conflicts_with": ", ".join(peers),
                "vessels": ", ".join(sorted(record.vessels)),
            }
            selected_value = value_map.get(self._sort_column, record.tag_name)
            if isinstance(selected_value, str):
                return selected_value.lower(), tag_name
            return selected_value, tag_name

        rows_to_show.sort(key=sort_key, reverse=self._sort_descending)

    def _show_context_menu(self, event: tk.Event) -> None:
        assert self._window.tree and self._window.context_menu
        clicked_item = self._window.tree.identify_row(event.y)
        if not clicked_item:
            return

        current_selection = set(self._window.tree.selection())
        if clicked_item not in current_selection:
            self._window.tree.selection_set(clicked_item)

        selected_count = len(self._window.tree.selection())
        if selected_count <= 1:
            align_label = "Align to Cimplicity"
            delete_label = "Delete Tag"
        else:
            align_label = f"Align {selected_count} tags to Cimplicity"
            delete_label = f"Delete {selected_count} tags"
        self._window.context_menu.entryconfigure(1, label=align_label)
        self._window.context_menu.entryconfigure(5, label=delete_label)
        self._window.context_menu.post(event.x_root, event.y_root)

    def _persist_tags(self) -> None:
        """Persists current in-memory table to tags.csv."""
        self._repository.save(self._tags)

    def refresh_from_disk(self) -> None:
        """Reloads the current database state from disk and refreshes UI."""
        self._tags = self._repository.load()
        self._refresh_filter_values()
        self.refresh_table()
        if not self._tags:
            messagebox.showwarning(
                "Database Missing or Empty",
                "No tags were loaded from disk.\n"
                "The database file may be missing or empty.",
            )

    def open_backups_page(self) -> None:
        """Opens full backup management page."""
        BackupsDialog(
            self._window.root,
            backup_service=self._backup_service,
            on_restore=self._restore_backup_from_page,
            on_revert_latest=self._revert_latest_backup_from_page,
        ).show()

    def apply_inline_find_replace(self) -> None:
        """Applies in-app find/replace from inline controls after confirmation."""
        find_text = self._window.find_text_var.get().strip()
        replace_text = self._window.replace_text_var.get()
        scope = self._window.find_scope_var.get()
        if not find_text:
            messagebox.showwarning("Invalid Input", "Find text cannot be empty.")
            return

        change_count = self._count_find_replace_changes(find_text, replace_text, scope)
        if change_count == 0:
            messagebox.showinfo(
                "Find & Replace",
                "No tags would be changed with the current find, replace, and scope settings.",
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Find & Replace",
            f"This will update {change_count} tag(s).\n\n"
            "Changes will be autosaved and batched for export.\n\n"
            "Continue?",
        )
        if not confirmed:
            return

        changed_count = self._apply_find_replace(find_text, replace_text, scope)
        if changed_count == 0:
            messagebox.showinfo("Find & Replace", "No matching rows were changed.")
            return

        self._persist_tags()
        self._refresh_filter_values()
        self.refresh_table()
        messagebox.showinfo(
            "Find & Replace Complete",
            f"Updated {changed_count} tag(s). Changes were autosaved and batched for export.",
        )

    def clear_inline_find_replace(self, refresh: bool = True) -> None:
        """Clears inline find/replace inputs."""
        self._window.find_text_var.set("")
        self._window.replace_text_var.set("")
        self._window.find_scope_var.set("both")
        if refresh:
            self.refresh_table()

    def _apply_find_replace(self, find_text: str, replace_text: str, scope: str) -> int:
        """Applies text replacement and returns number of changed tags."""
        changed_tags = 0
        pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)

        for tag_name in list(self._tags.keys()):
            record = self._tags[tag_name]
            old_tag_name = record.tag_name
            old_description = record.description
            old_vessels = set(record.vessels)
            old_row_data = dict(record.row_data)

            new_tag_name = old_tag_name
            new_description = old_description

            if scope in {"tag", "both"}:
                new_tag_name = pattern.sub(replace_text.upper(), old_tag_name).strip().upper()
            if scope in {"description", "both"}:
                new_description = pattern.sub(
                    replace_text.upper(), old_description
                ).strip().upper()

            if new_tag_name == old_tag_name and new_description == old_description:
                continue
            if not new_tag_name or not new_description:
                continue
            if new_tag_name != old_tag_name and new_tag_name in self._tags:
                continue

            self._tags.pop(old_tag_name)
            record.tag_name = new_tag_name
            record.description = new_description
            self._tags[new_tag_name] = record

            if old_tag_name in self._conflicted_tags:
                self._conflicted_tags.discard(old_tag_name)
                self._conflicted_tags.add(new_tag_name)

            updated_row = dict(old_row_data)
            updated_row["Name"] = new_tag_name
            updated_row["Description"] = new_description
            target_vessels = old_vessels or {"GLOBAL"}
            for vessel in target_vessels:
                self._queue_change(vessel=vessel, row_data=updated_row)
            changed_tags += 1

        return changed_tags

    @staticmethod
    def _preview_replace(source: str, pattern: re.Pattern[str], replace_text: str) -> str:
        return pattern.sub(replace_text.upper(), source).strip().upper()

    @staticmethod
    def _matches_find_scope(record: TagRecord, find_text: str, scope: str) -> bool:
        """True when find_text appears in the selected scope fields."""
        query = find_text.lower()
        if scope in {"tag", "both"} and query in record.tag_name.lower():
            return True
        if scope in {"description", "both"} and query in record.description.lower():
            return True
        return False

    @staticmethod
    def _highlight_find_text(text: str, find_text: str) -> str:
        """Wraps case-insensitive find matches with highlight markers for display."""
        if not find_text:
            return text
        pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)
        parts: list[str] = []
        last_index = 0
        for match in pattern.finditer(text):
            parts.append(text[last_index : match.start()])
            parts.append(f"[{match.group()}]")
            last_index = match.end()
        parts.append(text[last_index:])
        return "".join(parts)

    @staticmethod
    def _format_find_replace_display(
        tag_text: str,
        description_text: str,
        find_text: str,
        scope: str,
        highlight: bool,
    ) -> tuple[str, str]:
        """Applies find-match highlighting to scoped columns when requested."""
        if not highlight or not find_text:
            return tag_text, description_text
        display_tag = tag_text
        display_description = description_text
        if scope in {"tag", "both"}:
            display_tag = AppController._highlight_find_text(tag_text, find_text)
        if scope in {"description", "both"}:
            display_description = AppController._highlight_find_text(
                description_text, find_text
            )
        return display_tag, display_description

    def _count_find_replace_changes(
        self, find_text: str, replace_text: str, scope: str
    ) -> int:
        """Returns how many tags would change if find/replace were applied."""
        pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)
        _, change_count = self._build_live_preview_map(pattern, replace_text, scope)
        return change_count

    def _build_live_preview_map(
        self,
        pattern: re.Pattern[str] | None,
        replace_text: str,
        scope: str,
    ) -> tuple[dict[str, tuple[str, str]], int]:
        """
        Builds preview values using the same collision/validation rules as apply.
        Returns (map[tag_name] -> (preview_tag, preview_description), change_count).
        """
        preview_map: dict[str, tuple[str, str]] = {}
        if pattern is None or not replace_text:
            for tag_name, record in self._tags.items():
                preview_map[tag_name] = (record.tag_name, record.description)
            return preview_map, 0

        taken_tags = set(self._tags.keys())
        changed_count = 0
        for tag_name in list(self._tags.keys()):
            record = self._tags[tag_name]
            old_tag_name = record.tag_name
            old_description = record.description
            new_tag_name = old_tag_name
            new_description = old_description

            if scope in {"tag", "both"}:
                new_tag_name = self._preview_replace(old_tag_name, pattern, replace_text)
            if scope in {"description", "both"}:
                new_description = self._preview_replace(old_description, pattern, replace_text)

            valid_change = True
            if not new_tag_name or not new_description:
                valid_change = False
            if (
                valid_change
                and new_tag_name != old_tag_name
                and new_tag_name in taken_tags
            ):
                valid_change = False

            if valid_change and (new_tag_name != old_tag_name or new_description != old_description):
                changed_count += 1
                if new_tag_name != old_tag_name:
                    taken_tags.discard(old_tag_name)
                    taken_tags.add(new_tag_name)
                preview_map[tag_name] = (new_tag_name, new_description)
            else:
                preview_map[tag_name] = (old_tag_name, old_description)

        return preview_map, changed_count

    def _restore_backup_from_page(self, backup_name: str) -> bool:
        """Loads selected backup after saving temporary pre-load backup."""
        self._persist_tags()
        self._backup_service.create_preload_backup()
        self._backup_service.restore_backup(backup_name)
        self._tags = self._repository.load()
        self._refresh_filter_values()
        self.refresh_table()
        return True

    def _revert_latest_backup_from_page(self) -> bool:
        """Restores the temporary pre-load backup if available."""
        if not self._backup_service.restore_preload_backup():
            return False
        self._tags = self._repository.load()
        self._refresh_filter_values()
        self.refresh_table()
        return True

    def _update_pending_change_indicator(self) -> None:
        total = sum(len(changes) for changes in self._pending_changes.values())
        self._window.set_pending_change_count(total)

    def _queue_change(
        self,
        vessel: str,
        row_data: dict[str, str],
    ) -> None:
        self._pending_changes.setdefault(vessel, []).append({"row": dict(row_data)})
        self._update_pending_change_indicator()

    def _queue_change_if_different(
        self,
        vessel: str,
        original_row: dict[str, str],
        updated_row: dict[str, str],
    ) -> None:
        """Queues export only when Name, Description, or address actually changed."""
        if self._export_fields_for_compare(original_row) != self._export_fields_for_compare(
            updated_row
        ):
            self._queue_change(vessel=vessel, row_data=updated_row)

    @staticmethod
    def _export_fields_for_compare(row: dict[str, str]) -> dict[str, str]:
        """Extracts export-relevant fields so extra Proficy columns do not false-queue."""
        from services.address_normalizer import normalize_address

        name = str(row.get("Name", "")).strip().upper()
        description = str(row.get("Description", "")).strip().upper()
        address = ""
        for key in ("IOAddress", "Address", "ADDRESS", "ioaddress"):
            value = str(row.get(key, "")).strip()
            if value:
                address = normalize_address(value)
                break
        return {"Name": name, "Description": description, "Address": address}

    @staticmethod
    def _extract_address(row_data: dict[str, str]) -> str:
        """Gets address from row data using common key variants."""
        for key in (
            "Address",
            "ADDRESS",
            "address",
            "IOAddress",
            "IOADDRESS",
            "ioaddress",
        ):
            if key in row_data and str(row_data[key]).strip():
                return str(row_data[key]).strip().upper()
        return ""

    def _refresh_filter_values(self) -> None:
        assert self._window.vessel_combo
        vessels = sorted(
            {vessel for record in self._tags.values() for vessel in record.vessels}
        )
        self._window.vessel_combo["values"] = ["ALL", *vessels]
        if self._window.vessel_var.get() not in self._window.vessel_combo["values"]:
            self._window.vessel_var.set("ALL")
            self._active_vessel_filter = None

    def apply_vessel_filter(self, _: tk.Event | None = None) -> None:
        selected = self._window.vessel_var.get().strip().upper()
        self._active_vessel_filter = None if selected in {"", "ALL"} else selected
        self.refresh_table()

    def reset_vessel_filter(self) -> None:
        self._window.vessel_var.set("ALL")
        self._active_vessel_filter = None
        self.refresh_table()

    def _update_review_queue_indicator(self) -> None:
        self._window.set_review_queue_count(self._cross_program.review_queue.count())

    @staticmethod
    def _sync_status_label(status: str) -> str:
        return SYNC_STATUS_LABELS.get(status, status.replace("_", " ").title())

    def _passes_program_filter(self, record: TagRecord) -> bool:
        program_filter = self._window.program_filter_var.get().strip()
        if program_filter in {"", "ALL"}:
            return True
        if program_filter == "Proficy only":
            return bool(record.proficy_row_data) and not record.cimplicity_pt_id
        if program_filter == "Cimplicity only":
            return bool(record.cimplicity_pt_id or record.cimplicity_row_data)
        if program_filter == "Needs sync":
            return record.sync_status in {
                SYNC_PROFICY_DRIFT,
                SYNC_NEEDS_ALIGN,
                "name_mismatch",
            }
        return True

    def _record_address(self, record: TagRecord) -> str:
        if record.linked_address:
            return record.linked_address
        return self._extract_address(record.proficy_row_data)

    def _align_tags_to_cimplicity(self, tag_names: list[str]) -> int:
        aligned_count = 0
        for tag_name in tag_names:
            record = self._tags.get(tag_name)
            if record is None or not record.cimplicity_row_data:
                continue
            row = CimplicityImportRow(
                pt_id=record.cimplicity_pt_id or tag_name,
                description=normalize_description(record.cimplicity_row_data.get("DESC", "")),
                address=record.linked_address,
                row_data=dict(record.cimplicity_row_data),
                row_index=0,
            )
            export_row = self._cross_program.align_proficy_to_cimplicity(
                self._tags, tag_name, row, next(iter(record.vessels), "GLOBAL")
            )
            if export_row:
                for vessel in record.vessels or {"GLOBAL"}:
                    self._queue_change(vessel=vessel, row_data=export_row)
            aligned_count += 1
        self._persist_tags()
        self._update_pending_change_indicator()
        self.refresh_table()
        return aligned_count

    def align_selected_to_cimplicity(self) -> None:
        selected_tags = self._get_selected_tag_names()
        if not selected_tags:
            messagebox.showinfo(
                "Selection Required",
                "Select one or more tags in the main list to align.",
            )
            return
        aligned_count = self._align_tags_to_cimplicity(selected_tags)
        if aligned_count == 0:
            messagebox.showinfo(
                "No Cimplicity Link",
                "Selected tags are not linked to Cimplicity rows.",
            )
            return
        messagebox.showinfo("Aligned", f"Aligned {aligned_count} tag(s) to Cimplicity.")

    def open_cimplicity_review(self) -> None:
        CimplicityReviewDialog(
            self._window.root,
            review_queue=self._cross_program.review_queue,
            on_create_proficy=self._create_proficy_from_review_item,
            on_dismiss=self._dismiss_review_item,
        )

    def _create_proficy_from_review_item(self, item) -> None:
        from services.cimplicity_review_queue import ReviewQueueItem

        assert isinstance(item, ReviewQueueItem)
        row_data = {
            "Name": item.pt_id,
            "Description": item.description,
            "IOAddress": item.address,
            "Address": item.address,
        }
        self._cross_program.import_proficy_row(
            self._tags,
            tag_name=item.pt_id,
            description=item.description,
            vessel=item.vessel,
            row_data=row_data,
        )
        record = self._tags[item.pt_id]
        record.set_cimplicity_snapshot(item.row_data, item.vessel, "manual")
        record.cimplicity_pt_id = item.pt_id
        record.sync_status = SYNC_SYNCED
        self._cross_program.review_queue.remove(item.vessel, item.pt_id)
        self._persist_tags()
        self._update_review_queue_indicator()
        self._refresh_filter_values()
        self.refresh_table()

    def _dismiss_review_item(self, item) -> None:
        from services.cimplicity_review_queue import ReviewQueueItem

        assert isinstance(item, ReviewQueueItem)
        self._cross_program.review_queue.remove(item.vessel, item.pt_id)
        self._update_review_queue_indicator()

    def _on_view_conflicts_toggle(self) -> None:
        """Tracks conflict-view session behavior for inline resolution workflows."""
        if self._window.view_conflicts_var.get():
            self._recalculate_conflicted_tags()
            self._view_conflict_session_tags = set(self._conflicted_tags)
        else:
            self._view_conflict_session_tags.clear()
        self.refresh_table()

    def refresh_table(self) -> None:
        assert self._window.tree
        self._refresh_tree_heading_sort_markers()
        self._recalculate_conflicted_tags()
        query = self._window.search_var.get().strip().lower()
        view_conflicts_only = self._window.view_conflicts_var.get()

        if view_conflicts_only:
            self._view_conflict_session_tags.update(self._conflicted_tags)
            visible_conflict_scope = self._view_conflict_session_tags
        else:
            visible_conflict_scope = self._conflicted_tags

        rows_to_show: list[tuple[str, TagRecord]] = []
        find_text = self._window.find_text_var.get().strip()
        replace_text = self._window.replace_text_var.get()
        find_scope = self._window.find_scope_var.get()
        preview_on = self._window.preview_changes_var.get()
        find_pattern = (
            re.compile(re.escape(find_text), flags=re.IGNORECASE) if find_text else None
        )
        preview_map, preview_changes = self._build_live_preview_map(
            find_pattern, replace_text, find_scope
        )
        use_live_preview = bool(find_text and replace_text and preview_on)
        find_match_count = 0

        for tag_name, record in self._tags.items():
            if view_conflicts_only and tag_name not in visible_conflict_scope:
                continue
            if self._active_vessel_filter and self._active_vessel_filter not in record.vessels:
                continue
            if not self._passes_program_filter(record):
                continue
            if find_text and not self._matches_find_scope(record, find_text, find_scope):
                continue

            find_match_count += 1
            if use_live_preview:
                row_tag, row_description = preview_map[tag_name]
            else:
                row_tag = record.tag_name
                row_description = record.description

            vessels_text = ", ".join(sorted(record.vessels))
            address_text = self._record_address(record)
            peers_text = ", ".join(self._tag_conflict_peers.get(tag_name, []))
            searchable = (
                f"{row_tag} {row_description} {record.proficy_name} "
                f"{record.cimplicity_pt_id} {address_text} {vessels_text} {peers_text}"
            ).lower()
            if query and query not in searchable:
                continue
            rows_to_show.append((tag_name, record))

        self._sort_rows(rows_to_show)

        self._window.tree.delete(*self._window.tree.get_children())
        visible_groups: set[int] = set()

        for row_number, (tag_name, record) in enumerate(rows_to_show, start=1):
            if use_live_preview:
                row_tag, row_description = preview_map[tag_name]
            else:
                row_tag = record.tag_name
                row_description = record.description

            display_tag, display_description = self._format_find_replace_display(
                row_tag,
                row_description,
                find_text,
                find_scope,
                highlight=bool(find_text),
            )

            group_id = self._tag_conflict_group.get(tag_name)
            peers = self._tag_conflict_peers.get(tag_name, [])
            group_label = f"G{group_id}" if group_id is not None else ""
            conflicts_with = ", ".join(peers)
            vessels_text = ", ".join(sorted(record.vessels))
            address_text = self._record_address(record)
            proficy_name = record.proficy_name or ""
            cimplicity_pt = record.cimplicity_pt_id or ""
            sync_label = self._sync_status_label(record.sync_status)

            row_tags: list[str] = []
            if group_id is not None:
                color_index = (group_id - 1) % len(CONFLICT_GROUP_COLORS)
                row_tags.append(f"conflict_g{color_index}")
                visible_groups.add(group_id)
            elif record.sync_status in {SYNC_PROFICY_DRIFT, SYNC_NEEDS_ALIGN, "name_mismatch"}:
                row_tags.append("sync_drift")
            elif find_text:
                row_tags.append("find_match")

            self._window.tree.insert(
                "",
                "end",
                iid=tag_name,
                values=(
                    row_number,
                    display_tag,
                    proficy_name,
                    cimplicity_pt,
                    display_description,
                    address_text,
                    sync_label,
                    group_label,
                    conflicts_with,
                    vessels_text,
                ),
                tags=tuple(row_tags),
            )

        visible_count = len(rows_to_show)
        if view_conflicts_only:
            self._window.status_var.set(
                f"{visible_count} conflict tags in {len(visible_groups)} groups"
            )
        else:
            self._window.status_var.set(f"{visible_count} tags")
        self._window.set_find_replace_status(
            find_active=bool(find_text),
            match_count=find_match_count,
            change_count=preview_changes if replace_text else 0,
            preview_on=preview_on,
        )

    def _recalculate_conflicted_tags(self) -> None:
        """Builds conflict tag set and peer/group maps from current data."""
        descriptions_to_tags: dict[str, list[str]] = {}
        for tag_name, record in self._tags.items():
            description = record.description.strip().upper()
            if not description:
                continue
            descriptions_to_tags.setdefault(description, []).append(tag_name)

        recalculated: set[str] = set()
        peers_map: dict[str, list[str]] = {}
        group_map: dict[str, int] = {}
        group_id = 0

        for tag_names in descriptions_to_tags.values():
            if len(tag_names) <= 1:
                continue
            group_id += 1
            sorted_tags = sorted(tag_names)
            recalculated.update(sorted_tags)
            for tag_name in sorted_tags:
                group_map[tag_name] = group_id
                peers_map[tag_name] = [peer for peer in sorted_tags if peer != tag_name]

        self._conflicted_tags = recalculated
        self._tag_conflict_peers = {
            tag: peers_map[tag] for tag in recalculated if tag in peers_map
        }
        self._tag_conflict_group = {
            tag: group_map[tag] for tag in recalculated if tag in group_map
        }
        self._window.set_conflict_count(len(self._conflicted_tags))

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

        try:
            rows = self._loader.load_rows(file_path)
        except Exception as error:
            messagebox.showerror("Import Error", str(error))
            return

        original_rows = [dict(row) for row in rows]

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

        if not self._fill_missing_descriptions(rows, summary):
            return

        pending_conflicts: list[dict[str, object]] = []
        self._conflicted_tags = set()

        for row_index, row_data in enumerate(rows):
            imported_tag = row_data.get("Name", "").strip().upper()
            imported_description = row_data.get("Description", "").strip().upper()
            if not imported_tag:
                summary["rows_missing_name"] += 1
                continue

            existing_same_tag = self._tags.get(imported_tag)
            before_export = (
                existing_same_tag.proficy_export_row() if existing_same_tag is not None else None
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
                    self._queue_change_if_different(
                        vessel=vessel,
                        original_row=original_rows[row_index],
                        updated_row=after_export,
                    )
                elif before_export is not None:
                    self._queue_change_if_different(
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
                return

            for conflict, decision in zip(pending_conflicts, decisions):
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
                    self._queue_change_if_different(
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
                    self._queue_change_if_different(
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
                    self._queue_change_if_different(
                        vessel=vessel,
                        original_row=original_row,
                        updated_row=updated_row,
                    )
                    self._conflicted_tags.add(existing_tag)
                    self._conflicted_tags.add(new_tag)

        self._persist_tags()
        self._refresh_filter_values()
        self.clear_inline_find_replace(refresh=False)
        self.refresh_table()
        self._notify_import_complete(summary)

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

        summary = {
            "total_rows": len(prepared),
            "linked_synced": analysis.linked_synced,
            "auto_aligned": 0,
            "review_queue_added": analysis.review_queue_added,
            "actionable": len(analysis.actionable),
            "skipped": 0,
            "proficy_exports_queued": 0,
            "manual_cimplicity_flags": 0,
        }

        dialog_rows: list[dict[str, str]] = []
        for action in analysis.actionable:
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
        if dialog_rows:
            sync_dialog = CimplicitySyncDialog(self._window.root)
            result = sync_dialog.resolve_rows(vessel=vessel, rows=dialog_rows)
            sync_dialog.close()
            if result is None:
                return
            decisions = result

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
                        self._queue_change(vessel=vessel, row_data=export_row)
                        summary["proficy_exports_queued"] += 1
                elif action == "link_only" and changed:
                    summary["linked_synced"] += 1

            for row_index, row in enumerate(prepared, start=1):
                if row_index == 1 or row_index % 200 == 0:
                    loading_apply.update_status(
                        f"Linking unchanged rows... {row_index}/{len(prepared)}"
                    )
                if any(int(d.get("row_index", -1)) == row.row_index for d in decisions):
                    continue
                link = self._cross_program._linker.link_cimplicity_row(
                    self._tags, row.pt_id, row.address
                )
                if link.canonical_tag and not self._cross_program._detect_issues(
                    self._tags[link.canonical_tag], row
                ):
                    self._cross_program.apply_cimplicity_row(
                        self._tags, row, vessel, "link_only", canonical_tag=link.canonical_tag
                    )
                    summary["linked_synced"] += 1

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
            self._persist_tags()
            self._refresh_filter_values()
            self._update_review_queue_indicator()
            self.clear_inline_find_replace(refresh=False)
            self.refresh_table()
        finally:
            loading_apply.close()

        self._notify_cimplicity_import_complete(summary)

    def import_spreadsheet(self) -> None:
        """Backward-compatible alias for Proficy import."""
        self.import_proficy_spreadsheet()

    def _notify_cimplicity_import_complete(self, summary: dict[str, int]) -> None:
        messagebox.showinfo(
            "Cimplicity Import Complete",
            "Cimplicity Import Summary\n\n"
            f"Rows read: {summary['total_rows']}\n"
            f"Already synced (no action): {summary['linked_synced']}\n"
            f"Aligned Proficy to Cimplicity: {summary['auto_aligned']}\n"
            f"Sent to review queue: {summary['review_queue_added']}\n"
            f"Rows needing decisions: {summary['actionable']}\n"
            f"Skipped: {summary['skipped']}\n"
            f"Proficy exports queued: {summary['proficy_exports_queued']}\n"
            f"Manual Cimplicity flags: {summary['manual_cimplicity_flags']}\n\n"
            "Proficy batch files are generated via Export Changes.",
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

    def _fill_missing_descriptions(
        self, rows: list[dict[str, str]], summary: dict[str, int]
    ) -> bool:
        used_descriptions: set[str] = {
            record.description.strip().upper()
            for record in self._tags.values()
            if record.description.strip()
        }
        for row_data in rows:
            existing_description = row_data.get("Description", "").strip().upper()
            if existing_description:
                used_descriptions.add(existing_description)

        candidates: list[dict[str, object]] = []
        for index, row_data in enumerate(rows):
            tag_name = row_data.get("Name", "").strip().upper()
            description = row_data.get("Description", "").strip().upper()
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

        edited = MissingDescriptionDialog(self._window.root, candidates).show()
        if edited is None:
            return False

        for row_index, description in edited.items():
            if not description:
                continue
            rows[row_index]["Description"] = description
            summary["rows_missing_description_filled"] += 1
        return True

    def _notify_import_complete(self, summary: dict[str, int]) -> None:
        pending_rows = sum(len(changes) for changes in self._pending_changes.values())
        pending_vessels = len(self._pending_changes)
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

    def edit_selected_tag(self) -> None:
        assert self._window.tree
        selection = self._window.tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select a tag to edit first.")
            return

        old_tag = str(selection[0])
        record = self._tags[old_tag]
        old_description = record.description
        old_address = self._extract_address(record.row_data)
        old_vessels = set(record.vessels)
        old_row_data = dict(record.row_data)

        edited = EditTagDialog(
            self._window.root,
            tag_name=record.tag_name,
            description=record.description,
            address=old_address,
            vessels=set(record.vessels),
        ).show()
        if edited is None:
            return

        new_tag = str(edited["tag_name"]).strip().upper()
        new_description = str(edited["description"]).strip().upper()
        new_address = str(edited["address"]).strip().upper()
        new_vessels = set(edited["vessels"])
        if not new_tag:
            messagebox.showwarning("Invalid Tag", "Tag name cannot be empty.")
            return
        if not new_description:
            messagebox.showwarning("Invalid Description", "Description cannot be empty.")
            return
        if new_tag in self._tags and new_tag != old_tag:
            messagebox.showerror("Duplicate Tag", "That tag already exists.")
            return

        self._tags.pop(old_tag)
        record.tag_name = new_tag
        record.description = new_description
        record.vessels = new_vessels
        self._tags[new_tag] = record
        if old_tag in self._conflicted_tags:
            self._conflicted_tags.discard(old_tag)
            self._conflicted_tags.add(new_tag)
        self._persist_tags()

        has_changed = (
            old_tag != new_tag
            or old_description != new_description
            or old_address != new_address
            or old_vessels != new_vessels
        )
        record.proficy_row_data["Address"] = new_address
        record.proficy_row_data["IOAddress"] = new_address
        record.proficy_name = new_tag
        record.linked_address = new_address
        if record.cimplicity_pt_id:
            if record.description != normalize_description(
                record.cimplicity_row_data.get("DESC", record.description)
            ):
                record.sync_status = SYNC_PROFICY_DRIFT
            else:
                record.sync_status = SYNC_SYNCED
        if has_changed:
            target_vessels = new_vessels or old_vessels or {"GLOBAL"}
            updated_row = record.proficy_export_row()
            for vessel in target_vessels:
                self._queue_change(
                    vessel=vessel,
                    row_data=updated_row,
                )

        self._refresh_filter_values()
        self.refresh_table()
        messagebox.showinfo("Tag Updated", "Tag details were updated successfully.")

    def add_new_tag(self) -> None:
        """Creates a new tag for Proficy, Cimplicity, or both."""
        existing_vessels = sorted(
            {vessel for record in self._tags.values() for vessel in record.vessels}
        )
        created = AddTagDialog(self._window.root, existing_vessels).show()
        if created is None:
            return

        tag_name = str(created["tag_name"]).strip().upper()
        description = str(created["description"]).strip().upper()
        address = str(created["address"]).strip().upper()
        vessels = set(created["vessels"]) or {"GLOBAL"}
        program = str(created["program"]).strip().lower()
        queue_proficy = bool(created["queue_proficy"])

        if not tag_name:
            messagebox.showwarning("Invalid Tag", "Tag name cannot be empty.")
            return
        if not description:
            messagebox.showwarning("Invalid Description", "Description cannot be empty.")
            return
        if tag_name in self._tags:
            messagebox.showerror("Duplicate Tag", "That tag already exists.")
            return
        if program not in {"proficy", "cimplicity", "both"}:
            messagebox.showwarning("Invalid Program", "Program must be Proficy, Cimplicity, or Both.")
            return

        record = TagRecord(
            tag_name=tag_name,
            description=description,
            vessels=set(vessels),
        )
        if address:
            record.linked_address = address

        if program in {"proficy", "both"}:
            row_data = {
                "Name": tag_name,
                "Description": description,
            }
            if address:
                row_data["IOAddress"] = address
                row_data["Address"] = address
            record.set_proficy_snapshot(row_data, next(iter(vessels), "GLOBAL"))
            record.sync_status = SYNC_PROFICY_ONLY

        if program in {"cimplicity", "both"}:
            cim_row = {
                "PT_ID": tag_name,
                "DESC": description,
            }
            if address:
                cim_row["ADDR"] = address
            record.set_cimplicity_snapshot(cim_row, next(iter(vessels), "GLOBAL"), "manual")
            record.cimplicity_pt_id = tag_name
            if program == "both":
                record.sync_status = SYNC_SYNCED
            else:
                record.sync_status = SYNC_NEEDS_ALIGN

        self._tags[tag_name] = record
        self._persist_tags()

        if queue_proficy and program in {"proficy", "both"}:
            export_row = record.proficy_export_row()
            for vessel in vessels:
                self._queue_change(vessel=vessel, row_data=export_row)

        self._refresh_filter_values()
        self.refresh_table()
        messagebox.showinfo(
            "Tag Added",
            f"Created tag '{tag_name}' for {program.upper()} and updated the main list.",
        )

    def delete_selected_tags(self) -> None:
        """Deletes one or multiple selected tags with confirmation."""
        selected_tags = self._get_selected_tag_names()
        if not selected_tags:
            messagebox.showinfo("Selection Required", "Select at least one tag to delete.")
            return

        if len(selected_tags) == 1:
            tag_name = selected_tags[0]
            confirmed = messagebox.askyesno(
                "Delete Tag",
                f"Delete tag '{tag_name}'?\n\nThis cannot be undone.",
            )
        else:
            preview = ", ".join(selected_tags[:8])
            if len(selected_tags) > 8:
                preview += ", ..."
            confirmed = messagebox.askyesno(
                "Delete Tags",
                f"Delete {len(selected_tags)} selected tags?\n\n"
                f"Selected tags: {preview}\n\n"
                "This cannot be undone.",
            )

        if not confirmed:
            return

        for tag_name in selected_tags:
            record = self._tags.pop(tag_name, None)
            if record is not None:
                vessels = record.vessels or {"GLOBAL"}
                deleted_row = dict(record.row_data)
                deleted_row["Name"] = ""
                deleted_row["Description"] = record.description
                for vessel in vessels:
                    self._queue_change(
                        vessel=vessel,
                        row_data=deleted_row,
                    )
            self._conflicted_tags.discard(tag_name)
            self._tag_conflict_peers.pop(tag_name, None)
            self._tag_conflict_group.pop(tag_name, None)
            self._view_conflict_session_tags.discard(tag_name)

        self._persist_tags()
        self._refresh_filter_values()
        self.refresh_table()
        messagebox.showinfo("Deleted", f"Deleted {len(selected_tags)} tag(s).")

    def export_pending_changes(self) -> bool:
        """Writes all pending vessel batches to export files."""
        if not self._pending_changes:
            messagebox.showinfo("No Pending Changes", "There are no pending changes to export.")
            return True

        written_paths = self._export_service.write_exports(self._pending_changes)
        pending_count = sum(len(changes) for changes in self._pending_changes.values())
        self._pending_changes.clear()
        self._update_pending_change_indicator()
        rendered_paths = "\n".join(str(path) for path in written_paths)
        messagebox.showinfo(
            "Changes Exported",
            f"Exported {pending_count} changes.\n\nFiles:\n{rendered_paths}",
        )
        return True

    def _handle_app_close(self) -> None:
        """Prevents closing app while pending batches exist."""
        if not self._pending_changes:
            self._window.root.destroy()
            return

        close_choice = messagebox.askyesnocancel(
            "Pending Changes",
            "There are pending batched changes.\n\n"
            "Select Yes to export changes now.\n"
            "Select No to abort all pending changes.\n"
            "Select Cancel to go back to the application.",
        )
        if close_choice is None:
            return

        if close_choice:
            self.export_pending_changes()
            self._window.root.destroy()
            return

        confirm_abort = messagebox.askyesno(
            "Abort Pending Changes",
            "Abort and discard all pending batched changes?\n\nThis cannot be undone.",
        )
        if confirm_abort:
            self._pending_changes.clear()
            self._update_pending_change_indicator()
            self._window.root.destroy()

    def _get_selected_tag_names(self) -> list[str]:
        """Returns tag names from selected rows in the tree."""
        assert self._window.tree
        selected_tags: list[str] = []
        for item_id in self._window.tree.selection():
            tag_name = str(item_id)
            if tag_name in self._tags:
                selected_tags.append(tag_name)
        return selected_tags
