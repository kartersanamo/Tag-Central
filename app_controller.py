"""Application orchestration and event handlers."""

import tkinter as tk
from pathlib import Path
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

        self._window = MainWindow(root)
        self._bind_events()
        self._refresh_filter_values()
        self._recalculate_conflicted_tags()
        self.refresh_table()

    def _bind_events(self) -> None:
        assert self._window.import_button and self._window.save_button
        assert self._window.refresh_button and self._window.reset_filter_button
        assert self._window.change_tag_button and self._window.vessel_combo
        assert self._window.tree and self._window.context_menu

        self._window.import_button.configure(command=self.import_spreadsheet)
        self._window.save_button.configure(command=self.save_database_manual)
        self._window.refresh_button.configure(command=self.refresh_table)
        self._window.reset_filter_button.configure(command=self.reset_vessel_filter)
        self._window.change_tag_button.configure(command=self.edit_selected_tag)

        self._window.search_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.view_conflicts_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.vessel_combo.bind("<<ComboboxSelected>>", self.apply_vessel_filter)
        self._window.tree.bind("<Button-3>", self._show_context_menu)
        self._window.context_menu.entryconfigure(
            0, command=self.edit_selected_tag
        )

    def _show_context_menu(self, event: tk.Event) -> None:
        assert self._window.tree and self._window.context_menu
        selected = self._window.tree.identify_row(event.y)
        if not selected:
            return
        self._window.tree.selection_set(selected)
        self._window.context_menu.post(event.x_root, event.y_root)

    def save_database_manual(self) -> None:
        try:
            self._repository.save(self._tags)
            messagebox.showinfo("Saved", "Database saved successfully.")
        except OSError as error:
            messagebox.showerror("Save Error", str(error))

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

    def refresh_table(self) -> None:
        assert self._window.tree
        self._recalculate_conflicted_tags()
        query = self._window.search_var.get().strip().lower()
        view_conflicts_only = self._window.view_conflicts_var.get()

        rows_to_show: list[tuple[str, TagRecord]] = []
        for tag_name, record in self._tags.items():
            if view_conflicts_only and tag_name not in self._conflicted_tags:
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
            rows_to_show.sort(
                key=lambda item: (
                    self._tag_conflict_group.get(item[0], 999999),
                    item[1].description,
                    item[0],
                )
            )
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
            conflict_note = ""
            if self._conflicted_tags:
                group_count = len(
                    {self._tag_conflict_group[tag] for tag in self._conflicted_tags}
                )
                conflict_note = f" | {len(self._conflicted_tags)} conflicts in {group_count} groups"
            self._window.status_var.set(f"{visible_count} tags{conflict_note}")

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

        if self._conflicted_tags:
            recalculated.update(self._conflicted_tags)

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

        exports: dict[str, list[dict[str, object]]] = {}
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

        for row_data in rows:
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
                    self._conflicted_tags.add(imported_tag)
                    continue

                if action == "use_existing":
                    self._sync.add_vessel_to_existing(self._tags, existing_tag, vessel)
                    summary["resolved_use_existing"] += 1
                    summary["merged_to_existing"] += 1
                    self._add_export_if_changed(
                        exports,
                        vessel,
                        imported_tag,
                        existing_tag,
                        row_data,  # type: ignore[arg-type]
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
                    self._add_export_if_changed(
                        exports,
                        vessel,
                        imported_tag,
                        new_tag,
                        row_data,  # type: ignore[arg-type]
                    )
                    self._conflicted_tags.add(existing_tag)
                    self._conflicted_tags.add(new_tag)

        self._repository.save(self._tags)
        written = self._export_service.write_exports(exports) if exports else []
        self._refresh_filter_values()
        self.refresh_table()
        self._notify_import_complete(written, summary)

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

    def _notify_import_complete(
        self, written_paths: list[Path], summary: dict[str, int]
    ) -> None:
        export_rows = summary["resolved_use_existing"] + summary["resolved_keep_both"]

        export_section = "No export updates were needed."
        if written_paths:
            rendered_paths = "\n".join(str(path) for path in written_paths)
            export_section = (
                f"Export rows written: {export_rows}\n"
                f"Export files:\n{rendered_paths}\n\n"
                "Re-import these files into downstream systems as needed."
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
            f"{export_section}"
        )
        messagebox.showinfo("Import Complete", summary_text)

    @staticmethod
    def _add_export_if_changed(
        exports: dict[str, list[dict[str, object]]],
        vessel: str,
        old_tag: str,
        new_tag: str,
        row_data: dict[str, str],
    ) -> None:
        if old_tag == new_tag:
            return
        exports.setdefault(vessel, []).append(
            {"old_tag": old_tag, "new_tag": new_tag, "row": row_data}
        )

    def edit_selected_tag(self) -> None:
        assert self._window.tree
        selection = self._window.tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select a tag to edit first.")
            return

        current_values = self._window.tree.item(selection[0], "values")
        old_tag = str(current_values[0])
        record = self._tags[old_tag]

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

        written: list[Path] = []
        if old_tag != new_tag:
            exports = {
                "GLOBAL": [{"old_tag": old_tag, "new_tag": new_tag, "row": record.row_data}]
            }
            written = self._export_service.write_exports(exports)
        self._refresh_filter_values()
        self.refresh_table()
        if written:
            messagebox.showinfo(
                "Tag Updated",
                "Tag updated successfully.\n\n"
                "A rename export was generated because the tag name changed.",
            )
        else:
            messagebox.showinfo("Tag Updated", "Tag details were updated successfully.")
