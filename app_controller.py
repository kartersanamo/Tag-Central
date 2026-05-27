"""Application orchestration and event handlers."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from app_config import CONFLICT_GROUP_COLORS, DATABASE_FILE, EXPORT_FOLDER
from models.tag_record import TagRecord
from services.description_suggester import DescriptionSuggester
from services.export_service import ExportService
from services.spreadsheet_loader import SpreadsheetLoader
from services.tag_repository import TagRepository
from services.tag_sync_service import TagSyncService
from ui.conflict_dialog import ConflictDialog
from ui.edit_tag_dialog import EditTagDialog
from ui.main_window import MainWindow
from ui.missing_description_dialog import MissingDescriptionDialog


class AppController:
    """Coordinates UI, persistence, import logic, and exports."""

    def __init__(self, root: tk.Tk) -> None:
        self._repository = TagRepository(DATABASE_FILE)
        self._loader = SpreadsheetLoader()
        self._suggester = DescriptionSuggester()
        self._export_service = ExportService(EXPORT_FOLDER)
        self._sync = TagSyncService()
        self._tags: dict[str, TagRecord] = self._repository.load()
        self._active_vessel_filter: str | None = None
        self._conflicted_tags: set[str] = set()
        self._tag_conflict_peers: dict[str, list[str]] = {}
        self._tag_conflict_group: dict[str, int] = {}
        self._view_conflict_session_tags: set[str] = set()
        self._pending_changes: dict[str, list[dict[str, object]]] = {}

        self._window = MainWindow(root)
        self._bind_events()
        self._refresh_filter_values()
        self._recalculate_conflicted_tags()
        self._window.set_pending_change_count(0)
        self._window.root.protocol("WM_DELETE_WINDOW", self._handle_app_close)
        self.refresh_table()

    def _bind_events(self) -> None:
        assert self._window.import_button and self._window.save_button
        assert self._window.refresh_button and self._window.reset_filter_button
        assert self._window.export_changes_button
        assert self._window.change_tag_button and self._window.vessel_combo
        assert self._window.tree and self._window.context_menu

        self._window.import_button.configure(command=self.import_spreadsheet)
        self._window.save_button.configure(command=self.save_database_manual)
        self._window.refresh_button.configure(command=self.refresh_table)
        self._window.export_changes_button.configure(command=self.export_pending_changes)
        self._window.reset_filter_button.configure(command=self.reset_vessel_filter)
        self._window.change_tag_button.configure(command=self.edit_selected_tag)

        self._window.search_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.view_conflicts_var.trace_add(
            "write", lambda *_: self._on_view_conflicts_toggle()
        )
        self._window.vessel_combo.bind("<<ComboboxSelected>>", self.apply_vessel_filter)
        self._window.tree.bind("<Button-3>", self._show_context_menu)
        self._window.context_menu.entryconfigure(
            0, command=self.edit_selected_tag
        )
        self._window.context_menu.entryconfigure(
            1, command=self.delete_selected_tags
        )

    def _show_context_menu(self, event: tk.Event) -> None:
        assert self._window.tree and self._window.context_menu
        clicked_item = self._window.tree.identify_row(event.y)
        if not clicked_item:
            return

        current_selection = set(self._window.tree.selection())
        if clicked_item not in current_selection:
            self._window.tree.selection_set(clicked_item)

        selected_count = len(self._window.tree.selection())
        delete_label = "Delete Tag" if selected_count <= 1 else f"Delete {selected_count} tags"
        self._window.context_menu.entryconfigure(1, label=delete_label)
        self._window.context_menu.post(event.x_root, event.y_root)

    def save_database_manual(self) -> None:
        try:
            self._repository.save(self._tags)
            messagebox.showinfo("Saved", "Database saved successfully.")
        except OSError as error:
            messagebox.showerror("Save Error", str(error))

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
        """Queues change only when updated row differs from imported row."""
        if original_row != updated_row:
            self._queue_change(vessel=vessel, row_data=updated_row)

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
        self._recalculate_conflicted_tags()
        query = self._window.search_var.get().strip().lower()
        view_conflicts_only = self._window.view_conflicts_var.get()

        if view_conflicts_only:
            self._view_conflict_session_tags.update(self._conflicted_tags)
            visible_conflict_scope = self._view_conflict_session_tags
        else:
            visible_conflict_scope = self._conflicted_tags

        rows_to_show: list[tuple[str, TagRecord]] = []
        for tag_name, record in self._tags.items():
            if view_conflicts_only and tag_name not in visible_conflict_scope:
                continue
            if self._active_vessel_filter and self._active_vessel_filter not in record.vessels:
                continue

            vessels_text = ", ".join(sorted(record.vessels))
            peers_text = ", ".join(self._tag_conflict_peers.get(tag_name, []))
            searchable = (
                f"{record.tag_name} {record.description} {vessels_text} {peers_text}"
            ).lower()
            if query and query not in searchable:
                continue
            rows_to_show.append((tag_name, record))

        if view_conflicts_only:
            active_rows = [
                item for item in rows_to_show if item[0] in self._tag_conflict_group
            ]
            resolved_rows = [
                item for item in rows_to_show if item[0] not in self._tag_conflict_group
            ]
            active_rows.sort(
                key=lambda item: (
                    self._tag_conflict_group.get(item[0], 999999),
                    item[1].description,
                    item[0],
                )
            )
            resolved_rows.sort(key=lambda item: item[0])
            rows_to_show = active_rows + resolved_rows
        else:
            rows_to_show.sort(key=lambda item: item[0])

        self._window.tree.delete(*self._window.tree.get_children())
        visible_groups: set[int] = set()

        for tag_name, record in rows_to_show:
            group_id = self._tag_conflict_group.get(tag_name)
            peers = self._tag_conflict_peers.get(tag_name, [])
            group_label = f"G{group_id}" if group_id is not None else ""
            conflicts_with = ", ".join(peers)
            vessels_text = ", ".join(sorted(record.vessels))

            row_tags: tuple[str, ...] = ()
            if group_id is not None:
                color_index = (group_id - 1) % len(CONFLICT_GROUP_COLORS)
                row_tags = (f"conflict_g{color_index}",)
                visible_groups.add(group_id)

            self._window.tree.insert(
                "",
                "end",
                values=(
                    record.tag_name,
                    record.description,
                    group_label,
                    conflicts_with,
                    vessels_text,
                ),
                tags=row_tags,
            )

        visible_count = len(rows_to_show)
        if view_conflicts_only:
            self._window.status_var.set(
                f"{visible_count} conflict tags in {len(visible_groups)} groups"
            )
        else:
            self._window.status_var.set(f"{visible_count} tags")

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

    def import_spreadsheet(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Spreadsheet",
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
                self._sync.add_or_update_imported(
                    self._tags,
                    tag_name=imported_tag,
                    description=imported_description,
                    vessel=vessel,
                    row_data=row_data,
                )
                if existing_same_tag is None:
                    summary["new_tags_created"] += 1
                else:
                    summary["existing_tags_updated"] += 1
                updated_row = dict(row_data)
                updated_row["Name"] = imported_tag
                updated_row["Description"] = imported_description
                self._queue_change_if_different(
                    vessel=vessel,
                    original_row=original_rows[row_index],
                    updated_row=updated_row,
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

        self._repository.save(self._tags)
        self._refresh_filter_values()
        self.refresh_table()
        self._notify_import_complete(summary)

    def _fill_missing_descriptions(
        self, rows: list[dict[str, str]], summary: dict[str, int]
    ) -> bool:
        candidates: list[dict[str, object]] = []
        for index, row_data in enumerate(rows):
            tag_name = row_data.get("Name", "").strip().upper()
            description = row_data.get("Description", "").strip().upper()
            if tag_name and not description:
                candidates.append(
                    {
                        "row_index": index,
                        "tag": tag_name,
                        "suggested": self._suggester.suggest(tag_name),
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

        current_values = self._window.tree.item(selection[0], "values")
        old_tag = str(current_values[0])
        record = self._tags[old_tag]
        old_description = record.description
        old_vessels = set(record.vessels)
        old_row_data = dict(record.row_data)

        edited = EditTagDialog(
            self._window.root,
            tag_name=record.tag_name,
            description=record.description,
            vessels=set(record.vessels),
        ).show()
        if edited is None:
            return

        new_tag = str(edited["tag_name"]).strip().upper()
        new_description = str(edited["description"]).strip().upper()
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
        self._repository.save(self._tags)

        has_changed = (
            old_tag != new_tag
            or old_description != new_description
            or old_vessels != new_vessels
        )
        if has_changed:
            target_vessels = new_vessels or old_vessels or {"GLOBAL"}
            updated_row = dict(old_row_data)
            updated_row["Name"] = new_tag
            updated_row["Description"] = new_description
            for vessel in target_vessels:
                self._queue_change(
                    vessel=vessel,
                    row_data=updated_row,
                )

        self._refresh_filter_values()
        self.refresh_table()
        messagebox.showinfo("Tag Updated", "Tag details were updated successfully.")

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

        self._repository.save(self._tags)
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
            values = self._window.tree.item(item_id, "values")
            if not values:
                continue
            tag_name = str(values[0])
            if tag_name in self._tags:
                selected_tags.append(tag_name)
        return selected_tags
