"""Application orchestration and event handlers."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from app_config import DATABASE_FILE, EXPORT_FOLDER
from models.tag_record import TagRecord
from services.export_service import ExportService
from services.spreadsheet_loader import SpreadsheetLoader
from services.tag_repository import TagRepository
from services.tag_sync_service import TagSyncService
from ui.conflict_dialog import ConflictDialog
from ui.main_window import MainWindow


class AppController:
    """Coordinates UI, persistence, import logic, and exports."""

    def __init__(self, root: tk.Tk) -> None:
        self._repository = TagRepository(DATABASE_FILE)
        self._loader = SpreadsheetLoader()
        self._export_service = ExportService(EXPORT_FOLDER)
        self._sync = TagSyncService()
        self._tags: dict[str, TagRecord] = self._repository.load()
        self._active_vessel_filter: str | None = None

        self._window = MainWindow(root)
        self._bind_events()
        self._refresh_filter_values()
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
        self._window.change_tag_button.configure(command=self.rename_selected_tag)

        self._window.search_var.trace_add("write", lambda *_: self.refresh_table())
        self._window.vessel_combo.bind("<<ComboboxSelected>>", self.apply_vessel_filter)
        self._window.tree.bind("<Button-3>", self._show_context_menu)
        self._window.context_menu.entryconfigure(
            0, command=self.rename_selected_tag
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
        query = self._window.search_var.get().strip().lower()

        self._window.tree.delete(*self._window.tree.get_children())
        visible_count = 0

        for tag_name in sorted(self._tags):
            record = self._tags[tag_name]
            if self._active_vessel_filter and self._active_vessel_filter not in record.vessels:
                continue

            vessels_text = ", ".join(sorted(record.vessels))
            searchable = f"{record.tag_name} {record.description} {vessels_text}".lower()
            if query and query not in searchable:
                continue

            self._window.tree.insert(
                "",
                "end",
                values=(record.tag_name, record.description, vessels_text),
            )
            visible_count += 1

        self._window.status_var.set(f"{visible_count} tags")

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

        for row_data in rows:
            imported_tag = row_data.get("Name", "").strip().upper()
            imported_description = row_data.get("Description", "").strip().upper()
            if not imported_tag or not imported_description:
                continue

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
                self._add_export(exports, vessel, imported_tag, imported_tag, row_data)
                continue

            existing_tag, existing_record = conflict
            resolution = ConflictDialog(
                self._window.root,
                vessel=vessel,
                imported_tag=imported_tag,
                imported_description=imported_description,
                existing_tag=existing_tag,
                existing_description=existing_record.description,
            ).show()

            action = resolution.get("action", "skip")
            if action == "skip":
                continue

            if action == "use_imported":
                self._sync.add_or_update_imported(
                    self._tags,
                    tag_name=imported_tag,
                    description=imported_description,
                    vessel=vessel,
                    row_data=row_data,
                )
                self._add_export(exports, vessel, imported_tag, imported_tag, row_data)
                continue

            if action == "use_existing":
                resolved_tag = resolution["resolved_tag"]
                self._sync.add_vessel_to_existing(self._tags, resolved_tag, vessel)
                self._add_export(exports, vessel, imported_tag, resolved_tag, row_data)
                continue

            if action == "keep_both":
                new_tag = self._sync.unique_suffix_name(self._tags, imported_tag)
                self._sync.add_or_update_imported(
                    self._tags,
                    tag_name=new_tag,
                    description=imported_description,
                    vessel=vessel,
                    row_data=row_data,
                )
                self._add_export(exports, vessel, imported_tag, new_tag, row_data)

        self._repository.save(self._tags)
        written = self._export_service.write_exports(exports) if exports else []
        self._refresh_filter_values()
        self.refresh_table()
        self._notify_import_complete(written)

    def _notify_import_complete(self, written_paths: list[Path]) -> None:
        if not written_paths:
            messagebox.showinfo("Import Complete", "Import completed with no export updates.")
            return

        rendered_paths = "\n".join(str(path) for path in written_paths)
        messagebox.showinfo(
            "Import Complete",
            "Import completed. Export files were generated:\n\n"
            f"{rendered_paths}\n\n"
            "Re-import these files into downstream systems as needed.",
        )

    @staticmethod
    def _add_export(
        exports: dict[str, list[dict[str, object]]],
        vessel: str,
        old_tag: str,
        new_tag: str,
        row_data: dict[str, str],
    ) -> None:
        exports.setdefault(vessel, []).append(
            {"old_tag": old_tag, "new_tag": new_tag, "row": row_data}
        )

    def rename_selected_tag(self) -> None:
        assert self._window.tree
        selection = self._window.tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select a tag to rename first.")
            return

        current_values = self._window.tree.item(selection[0], "values")
        old_tag = str(current_values[0])

        new_tag = simpledialog.askstring("Rename Tag", f"Rename '{old_tag}' to:")
        if not new_tag:
            return
        new_tag = new_tag.strip().upper()
        if not new_tag:
            messagebox.showwarning("Invalid Tag", "Tag name cannot be empty.")
            return
        if new_tag in self._tags and new_tag != old_tag:
            messagebox.showerror("Duplicate Tag", "That tag already exists.")
            return

        record = self._tags.pop(old_tag)
        record.tag_name = new_tag
        self._tags[new_tag] = record
        self._repository.save(self._tags)

        exports = {"GLOBAL": [{"old_tag": old_tag, "new_tag": new_tag, "row": record.row_data}]}
        written = self._export_service.write_exports(exports)
        self._refresh_filter_values()
        self.refresh_table()
        self._notify_import_complete(written)
