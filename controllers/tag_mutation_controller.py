"""TagMutation orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

import re

from tkinter import messagebox

from app_config import BULK_DELETE_BACKUP_THRESHOLD
from models.tag_record import (
    SYNC_NAME_MISMATCH,
    SYNC_PROFICY_DRIFT,
    SYNC_SYNCED,
    TagRecord,
)
from services.address_normalizer import is_resolvable_address, normalize_address
from services.cross_program_sync_service import (
    CimplicityImportRow,
    normalize_description,
)
from services.internal_mismatch_service import MISMATCH_DUPLICATE_DESCRIPTION
from services.tag_address import extract_address, record_address
from ui.add_tag_dialog import AddTagDialog
from ui.edit_tag_dialog import EditTagDialog
from ui.loading_dialog import LoadingDialog
from ui.merge_tags_dialog import MergeTagsDialog
from ui.tag_diff_dialog import TagDiffDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class TagMutationController(ControllerBase):
    """Extracted from AppController — tag_mutation_controller."""

    def view_selected_tag_diff(self) -> None:
        selection = self._app._get_selected_tag_names()
        if len(selection) != 1:
            return
        record = self._tags.get(selection[0])
        if record is None:
            return
        TagDiffDialog(self._window.root, record)


    def merge_selected_tags(self) -> None:
        selection = self._app._get_selected_tag_names()
        if len(selection) != 2:
            messagebox.showinfo("Merge Tags", "Select exactly two tags to merge.")
            return
        tag_a, tag_b = selection[0], selection[1]
        survivor = MergeTagsDialog(self._window.root, tag_a, tag_b).show()
        if survivor is None:
            return
        secondary = tag_b if survivor == tag_a else tag_a
        try:
            record = self._merge_service.merge_tags(self._tags, survivor, secondary)
        except KeyError as error:
            messagebox.showerror("Merge Failed", str(error))
            return
        export_row = record.proficy_export_row()
        for vessel in record.vessels or {"GLOBAL"}:
            self._app._queue_change(vessel=vessel, row_data=export_row)
        self._ctx.persist_tags()
        self._app._recalculate_conflicted_tags()
        self._app._refresh_filter_values()
        self._app.refresh_table()
        messagebox.showinfo("Merge Complete", f"Merged into '{survivor}'.")


    def _description_increment_base(description: str) -> str:
        """Strips a trailing numeric suffix before re-numbering descriptions."""
        trimmed = description.strip().upper()
        return re.sub(r" \d+$", "", trimmed)


    def _can_increment_descriptions(self, tag_names: list[str]) -> bool:
        """True when mismatch view is on and all selected share a description group."""
        if not self._window.view_conflicts_var.get():
            return False
        if len(tag_names) < 2:
            return False

        group_labels: set[str] = set()
        for tag_name in tag_names:
            if self._tag_mismatch_type.get(tag_name) != MISMATCH_DUPLICATE_DESCRIPTION:
                return False
            label = self._tag_mismatch_group_label.get(tag_name)
            if not label or not label.startswith("G"):
                return False
            group_labels.add(label)
        return len(group_labels) == 1


    def increment_selected_descriptions(self) -> None:
        """Assigns '{base} 1', '{base} 2', ... to tags in one internal mismatch group."""
        assert self._window.tree
        selection = list(self._window.tree.selection())
        if not self._can_increment_descriptions(selection):
            messagebox.showinfo(
                "Increment Descriptions",
                "Select two or more tags from the same group while "
                "View Internal Mismatches is enabled.",
            )
            return

        sorted_tags = sorted(selection)
        first_record = self._tags[sorted_tags[0]]
        base_description = self._description_increment_base(first_record.description)
        if not base_description:
            messagebox.showwarning(
                "Increment Descriptions", "Cannot increment empty descriptions."
            )
            return

        preview_lines = [
            f"{tag_name}: {base_description} {index}"
            for index, tag_name in enumerate(sorted_tags, start=1)
        ]
        confirmed = messagebox.askyesno(
            "Increment Descriptions",
            "Apply numbered descriptions to the selected tags?\n\n"
            + "\n".join(preview_lines[:12])
            + ("\n..." if len(preview_lines) > 12 else "")
            + "\n\nChanges will be autosaved and batched for Proficy export.",
        )
        if not confirmed:
            return

        updated_count = 0
        for index, tag_name in enumerate(sorted_tags, start=1):
            record = self._tags.get(tag_name)
            if record is None:
                continue

            old_description = record.description
            old_sync_status = record.sync_status
            old_cimplicity_pt_id = record.cimplicity_pt_id
            new_description = f"{base_description} {index}"
            if old_description == new_description:
                continue

            record.description = new_description
            if record.proficy_row_data:
                record.proficy_row_data["Description"] = new_description

            if record.cimplicity_pt_id:
                cim_desc = normalize_description(
                    record.cimplicity_row_data.get("DESC", record.description)
                )
                if record.description != cim_desc:
                    record.sync_status = SYNC_PROFICY_DRIFT
                elif (record.proficy_name or tag_name) != record.cimplicity_pt_id:
                    record.sync_status = SYNC_NAME_MISMATCH
                else:
                    record.sync_status = SYNC_SYNCED

            target_vessels = record.vessels or {"GLOBAL"}
            export_row = record.proficy_export_row()
            for vessel in target_vessels:
                self._app._queue_change(vessel=vessel, row_data=export_row)

            if old_sync_status == SYNC_SYNCED and old_cimplicity_pt_id:
                task_vessel = next(iter(target_vessels))
                self._manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="description",
                    old_value=old_description,
                    new_value=new_description,
                    reason="Numbered descriptions for internal mismatch resolution",
                )
            updated_count += 1

        if updated_count == 0:
            messagebox.showinfo("Increment Descriptions", "No descriptions were changed.")
            return

        self._ctx.persist_tags()
        self._app._recalculate_conflicted_tags()
        self._app._update_manual_tasks_indicator()
        self._app._refresh_filter_values()
        self._app.refresh_table()
        messagebox.showinfo(
            "Increment Descriptions",
            f"Updated {updated_count} tag description(s). "
            "Changes were autosaved and batched for export.",
        )


    def _align_tags_to_cimplicity(self, tag_names: list[str]) -> int:
        aligned_count = 0
        loading = LoadingDialog(self._window.root, title="Aligning to Cimplicity...")
        loading.show("Aligning selected tags...")
        try:
            for index, tag_name in enumerate(tag_names, start=1):
                if index == 1 or index % 50 == 0:
                    loading.update_status(f"Aligning tags... {index}/{len(tag_names)}")
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
                        self._app._queue_change(vessel=vessel, row_data=export_row)
                aligned_count += 1
            loading.update_status("Saving aligned data...")
            self._ctx.persist_tags()
            self._app._update_pending_change_indicator()
            self._app.refresh_table()
        finally:
            loading.close()
        return aligned_count


    def align_selected_to_cimplicity(self) -> None:
        selected_tags = self._app._get_selected_tag_names()
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


    def edit_selected_tag(self) -> None:
        assert self._window.tree
        selection = self._window.tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select a tag to edit first.")
            return

        old_tag = str(selection[0])
        record = self._tags[old_tag]
        old_description = record.description
        old_address = extract_address(record.row_data)
        old_vessels = set(record.vessels)
        old_row_data = dict(record.row_data)
        old_sync_status = record.sync_status
        old_cimplicity_pt_id = record.cimplicity_pt_id

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
        self._ctx.persist_tags()

        has_changed = (
            old_tag != new_tag
            or old_description != new_description
            or old_address != new_address
            or old_vessels != new_vessels
        )
        record.proficy_row_data["Address"] = new_address
        record.proficy_row_data["IOAddress"] = new_address
        record.proficy_name = new_tag
        if is_resolvable_address(new_address):
            record.linked_address = normalize_address(new_address)
        elif not record.cimplicity_pt_id:
            record.linked_address = ""
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
                self._app._queue_change(
                    vessel=vessel,
                    row_data=updated_row,
                )

        if old_sync_status == SYNC_SYNCED and old_cimplicity_pt_id:
            task_vessel = next(iter(new_vessels or old_vessels or {"GLOBAL"}))
            if old_tag != new_tag:
                self._manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="tag_name",
                    old_value=old_tag,
                    new_value=new_tag,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )
            if old_description != new_description:
                self._manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="description",
                    old_value=old_description,
                    new_value=new_description,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )
            if old_address != new_address:
                self._manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="address",
                    old_value=old_address,
                    new_value=new_address,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )
            self._app._update_manual_tasks_indicator()

        self._app._refresh_filter_values()
        self._app.refresh_table()


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
        if address and is_resolvable_address(address):
            record.linked_address = normalize_address(address)

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
        self._ctx.persist_tags()

        if queue_proficy and program in {"proficy", "both"}:
            export_row = record.proficy_export_row()
            for vessel in vessels:
                self._app._queue_change(vessel=vessel, row_data=export_row)

        self._app._refresh_filter_values()
        self._app.refresh_table()
        messagebox.showinfo(
            "Tag Added",
            f"Created tag '{tag_name}' for {program.upper()} and updated the main list.",
        )


    def delete_selected_tags(self) -> None:
        """Deletes one or multiple selected tags with confirmation."""
        selected_tags = self._app._get_selected_tag_names()
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

        if len(selected_tags) >= BULK_DELETE_BACKUP_THRESHOLD:
            self._app._auto_backup_before_bulk("delete_tags")

        loading_delete = LoadingDialog(self._window.root, title="Deleting Tags...")
        loading_delete.show("Deleting selected tags...")
        try:
            for index, tag_name in enumerate(selected_tags, start=1):
                if index == 1 or index % 100 == 0:
                    loading_delete.update_status(f"Deleting tags... {index}/{len(selected_tags)}")
                record = self._tags.pop(tag_name, None)
                if record is not None:
                    vessels = record.vessels or {"GLOBAL"}
                    deleted_row = dict(record.row_data)
                    deleted_row["Name"] = ""
                    deleted_row["Description"] = record.description
                    for vessel in vessels:
                        self._app._queue_change(
                            vessel=vessel,
                            row_data=deleted_row,
                        )
                self._conflicted_tags.discard(tag_name)
                self._tag_conflict_peers.pop(tag_name, None)
                self._tag_mismatch_group_label.pop(tag_name, None)
                self._tag_mismatch_type.pop(tag_name, None)

            loading_delete.update_status("Saving deletion changes...")
            self._ctx.persist_tags()
            self._app._refresh_filter_values()
            self._app.refresh_table()
        finally:
            loading_delete.close()
        messagebox.showinfo("Deleted", f"Deleted {len(selected_tags)} tag(s).")

