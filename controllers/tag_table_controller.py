"""TagTable orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

import re
import sys

import tkinter as tk
from tkinter import messagebox

from app_config import (
    ASYNC_TABLE_THRESHOLD,
    BULK_DELETE_BACKUP_THRESHOLD,
    CONFLICT_GROUP_COLORS,
    PERSIST_DEBOUNCE_MS,
)
from models.tag_record import (
    SYNC_NEEDS_ALIGN,
    SYNC_NAME_MISMATCH,
    SYNC_PROFICY_DRIFT,
    TagRecord,
)
from services.find_replace_service import (
    format_find_replace_display,
    highlight_find_text,
    matches_find_scope,
    preview_replace,
)
from services.internal_mismatch_service import (
    MISMATCH_DUPLICATE_DESCRIPTION,
    MISMATCH_PT_ID_PREFIX,
    MISMATCH_SHARED_ADDRESS,
)
from services.tag_address import record_address
from services.sync_status_labels import sync_status_label
from ui.loading_dialog import LoadingDialog

ARRAY_INDEX_PATTERN = re.compile(r"^(?P<base>.+)\[(?P<index>\d+)\]$")

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class TagTableController(ControllerBase):
    """Extracted from AppController — tag_table_controller."""

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
            group_label = self._tag_mismatch_group_label.get(tag_name, "")
            peers = self._tag_conflict_peers.get(tag_name, [])

            value_map: dict[str, object] = {
                "row_number": tag_name,
                "tag_name": record.tag_name,
                "proficy_name": record.proficy_name or "",
                "cimplicity_pt_id": record.cimplicity_pt_id or "",
                "description": record.description,
                "address": record_address(record),
                "sync_status": sync_status_label(record.sync_status),
                "conflict_group": group_label or "zzz",
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

        selection = list(self._window.tree.selection())
        selected_count = len(selection)
        copy_label = (
            "Copy Tag"
            if selected_count <= 1
            else f"Copy {selected_count} Tags"
        )
        self._window.context_menu.entryconfigure(
            1,
            label=copy_label,
            state="normal" if selected_count else "disabled",
        )

        if selected_count <= 1:
            align_label = "Align to Cimplicity"
            delete_label = "Delete Tag"
        else:
            align_label = f"Align {selected_count} tags to Cimplicity"
            delete_label = f"Delete {selected_count} tags"
        self._window.context_menu.entryconfigure(2, label=align_label)
        self._window.context_menu.entryconfigure(12, label=delete_label)

        array_toggle_label = "Toggle Array Indices"
        can_toggle_array = False
        if len(selection) == 1:
            canonical = self._canonical_tag_name(selection[0])
            if canonical and self._is_array_parent(canonical):
                can_toggle_array = True
                array_toggle_label = (
                    "Hide Array Indices"
                    if canonical in self._expanded_array_bases
                    else "Show Array Indices"
                )
        self._window.context_menu.entryconfigure(
            3,
            label=array_toggle_label,
            state="normal" if can_toggle_array else "disabled",
        )

        jump_candidates = self._selected_mismatch_group_tags(selection)
        can_jump = len(jump_candidates) > 1
        self._window.context_menu.entryconfigure(
            4, state="normal" if can_jump else "disabled"
        )

        can_diff = (
            len(selection) == 1
            and selection[0] in self._tags
            and (
                self._tags[selection[0]].cimplicity_pt_id
                or self._tags[selection[0]].proficy_row_data
            )
        )
        self._window.context_menu.entryconfigure(
            5, state="normal" if can_diff else "disabled"
        )

        can_merge = len(selection) == 2 and all(tag in self._tags for tag in selection)
        self._window.context_menu.entryconfigure(
            8, state="normal" if can_merge else "disabled"
        )

        can_increment = self._app._can_increment_descriptions(selection)
        if can_increment:
            increment_label = (
                f"Increment descriptions ({selected_count})"
                if selected_count > 1
                else "Increment descriptions"
            )
            increment_state = "normal"
        else:
            increment_label = "Increment descriptions"
            increment_state = "disabled"
        self._window.context_menu.entryconfigure(
            6, label=increment_label, state=increment_state
        )
        self._window.context_menu.post(event.x_root, event.y_root)


    def _on_copy_tags_shortcut(self, event: tk.Event) -> str:
        """Copies selected tag rows when the table has focus."""
        self.copy_selected_tags()
        return "break"


    def _clipboard_column_headers(self) -> list[str]:
        return [
            "Tag",
            "Proficy Name",
            "Cimplicity PT_ID",
            "Description",
            "Address",
            "Sync",
            "Group",
            "Vessels",
        ]


    def _escape_tsv_field(value: str) -> str:
        """Quotes clipboard fields that contain tabs or line breaks."""
        if any(character in value for character in ('\t', '\n', '\r', '"')):
            return '"' + value.replace('"', '""') + '"'
        return value


    def _tag_clipboard_row_values(self, tag_name: str, record: TagRecord) -> list[str]:
        group_label = self._tag_mismatch_group_label.get(tag_name, "")
        values = [
            record.tag_name,
            record.proficy_name or "",
            record.cimplicity_pt_id or "",
            record.description,
            record_address(record),
            sync_status_label(record.sync_status),
            group_label,
            ", ".join(sorted(record.vessels)),
        ]
        return [self._escape_tsv_field(value) for value in values]


    def copy_selected_tags(self) -> None:
        """Copies selected tag row values to the system clipboard (tab-separated)."""
        selected_tags = self._get_selected_tag_names()
        if not selected_tags:
            return

        lines = ["\t".join(self._clipboard_column_headers())]
        for tag_name in sorted(selected_tags):
            record = self._tags.get(tag_name)
            if record is None:
                continue
            lines.append(
                "\t".join(self._tag_clipboard_row_values(tag_name, record))
            )

        clipboard_text = "\n".join(lines)
        self._window.root.clipboard_clear()
        self._window.root.clipboard_append(clipboard_text)
        self._window.root.update_idletasks()


    def _on_tree_double_click(self, event: tk.Event) -> None:
        assert self._window.tree
        item_id = self._window.tree.identify_row(event.y)
        if not item_id:
            return
        tag_name = self._canonical_tag_name(item_id)
        if not tag_name:
            return
        self._window.tree.selection_set(tag_name)
        self._app.edit_selected_tag()


    def _selected_mismatch_group_tags(self, tag_names: list[str]) -> list[str]:
        """Returns sorted tags in the clicked/selected mismatch group."""
        if not tag_names:
            return []
        group_label = self._tag_mismatch_group_label.get(tag_names[0])
        if not group_label:
            return []
        return sorted(
            tag_name
            for tag_name in self._conflicted_tags
            if self._tag_mismatch_group_label.get(tag_name) == group_label
        )


    def jump_to_selected_mismatches(self) -> None:
        """Focuses first row of mismatch group and selects the whole group."""
        assert self._window.tree
        selection = list(self._window.tree.selection())
        group_tags = self._selected_mismatch_group_tags(selection)
        if len(group_tags) <= 1:
            messagebox.showinfo(
                "Jump to Mismatches",
                "Right-click a tag with internal mismatches to jump to its group.",
            )
            return

        current_rows = [str(row_id) for row_id in self._window.tree.get_children("")]
        visible_group_rows = [tag for tag in current_rows if tag in group_tags]
        if not visible_group_rows:
            messagebox.showinfo(
                "Jump to Mismatches",
                "No matching mismatch group rows are visible with current filters.",
            )
            return

        first_row = visible_group_rows[0]
        self._window.tree.selection_set(visible_group_rows)
        self._window.tree.focus(first_row)
        self._window.root.after_idle(
            lambda row=first_row: self._scroll_tree_row_to_center(row)
        )


    def _scroll_tree_row_to_center(self, item_id: str) -> None:
        """Scrolls the table so item_id sits near the vertical center of the viewport."""
        assert self._window.tree
        tree = self._window.tree
        children = list(tree.get_children(""))
        if item_id not in children:
            tree.see(item_id)
            return

        index = children.index(item_id)
        total = len(children)
        tree.update_idletasks()

        row_height = 22
        for child in children[: min(8, total)]:
            bbox = tree.bbox(child)
            if bbox:
                row_height = max(bbox[3], 18)
                break

        viewport_height = max(tree.winfo_height(), row_height)
        visible_rows = max(1, viewport_height // row_height)

        if total <= visible_rows:
            tree.yview_moveto(0)
            return

        top_index = max(0, min(index - visible_rows // 2, total - visible_rows))
        fraction = top_index / (total - visible_rows)
        tree.yview_moveto(fraction)


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

        self._ctx.schedule_persist()
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


    def delete_inline_find_matches(self) -> None:
        """Deletes all tags matching current Find/Scope with strong confirmation."""
        find_text = self._window.find_text_var.get().strip()
        scope = self._window.find_scope_var.get()
        if not find_text:
            messagebox.showwarning(
                "Invalid Input", "Enter Find text before deleting matches."
            )
            return

        matching_tags = [
            tag_name
            for tag_name, record in self._tags.items()
            if matches_find_scope(record, find_text, scope)
        ]
        if not matching_tags:
            messagebox.showinfo(
                "Delete Matches", "No tags match the current Find and Scope."
            )
            return

        preview = ", ".join(matching_tags[:10])
        if len(matching_tags) > 10:
            preview += ", ..."
        confirmed = messagebox.askyesno(
            "DANGER: Delete All Matching Tags",
            f"IMPORTANT: This will permanently delete {len(matching_tags)} tag(s)\n"
            f"matching Find '{find_text}' in scope '{scope}'.\n\n"
            f"Examples: {preview}\n\n"
            "This action cannot be undone.\n"
            "Proficy delete rows will be queued for export.\n\n"
            "Are you absolutely sure you want to continue?",
            icon=messagebox.WARNING,
        )
        if not confirmed:
            return

        if len(matching_tags) >= BULK_DELETE_BACKUP_THRESHOLD:
            self._app._auto_backup_before_bulk("find_delete_matches")

        loading_delete = LoadingDialog(
            self._window.root, title="Deleting Find Matches..."
        )
        loading_delete.show("Deleting matching tags...")
        try:
            for index, tag_name in enumerate(matching_tags, start=1):
                if index == 1 or index % 100 == 0:
                    loading_delete.update_status(
                        f"Deleting matches... {index}/{len(matching_tags)}"
                    )
                record = self._tags.pop(tag_name, None)
                if record is not None:
                    vessels = record.vessels or {"GLOBAL"}
                    deleted_row = dict(record.row_data)
                    deleted_row["Name"] = ""
                    deleted_row["Description"] = record.description
                    for vessel in vessels:
                        self._app._queue_change(vessel=vessel, row_data=deleted_row)

                self._conflicted_tags.discard(tag_name)
                self._tag_conflict_peers.pop(tag_name, None)
                self._tag_mismatch_group_label.pop(tag_name, None)
                self._tag_mismatch_type.pop(tag_name, None)

            loading_delete.update_status("Saving deletion changes...")
            self._ctx.persist_tags()
            self._refresh_filter_values()
            self.refresh_table()
        finally:
            loading_delete.close()

        messagebox.showinfo(
            "Delete Matches Complete",
            f"Deleted {len(matching_tags)} matching tag(s).",
        )


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
            if new_tag_name != old_tag_name:
                record.proficy_name = new_tag_name
            if record.proficy_row_data:
                record.proficy_row_data["Name"] = new_tag_name
                record.proficy_row_data["Description"] = new_description
            self._tags[new_tag_name] = record

            if old_tag_name in self._conflicted_tags:
                self._conflicted_tags.discard(old_tag_name)
                self._conflicted_tags.add(new_tag_name)

            updated_row = dict(old_row_data)
            updated_row["Name"] = new_tag_name
            updated_row["Description"] = new_description
            target_vessels = old_vessels or {"GLOBAL"}
            for vessel in target_vessels:
                self._app._queue_change(vessel=vessel, row_data=updated_row)
            changed_tags += 1

        return changed_tags


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
                new_tag_name = preview_replace(old_tag_name, pattern, replace_text)
            if scope in {"description", "both"}:
                new_description = preview_replace(old_description, pattern, replace_text)

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
        self._window.program_filter_var.set("ALL")
        self._active_vessel_filter = None
        self.refresh_table()


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
                SYNC_NAME_MISMATCH,
            }
        return True


    def _on_view_conflicts_toggle(self) -> None:
        """Tracks internal-mismatch view session behavior for inline resolution."""
        if self._window.view_conflicts_var.get():
            self._recalculate_conflicted_tags()
            self._expand_arrays_for_conflicted_tags()
            if self._sort_before_internal_mismatches is None:
                self._sort_before_internal_mismatches = (
                    self._sort_column,
                    self._sort_descending,
                )
            self._sort_column = "conflict_group"
            self._sort_descending = False
        else:
            if self._sort_before_internal_mismatches is not None:
                self._sort_column, self._sort_descending = (
                    self._sort_before_internal_mismatches
                )
                self._sort_before_internal_mismatches = None
        self.refresh_table()


    def refresh_table(self) -> None:
        assert self._window.tree
        assert self._window.array_expand_toggle_button
        self._refresh_tree_heading_sort_markers()
        self._recalculate_conflicted_tags()
        self._rebuild_array_index_map()
        if not self._array_children_by_base:
            self._window.array_expand_toggle_button.configure(
                text="Expand All", state="disabled"
            )
        elif len(self._expanded_array_bases) >= len(self._array_children_by_base):
            self._window.array_expand_toggle_button.configure(
                text="Collapse All", state="normal"
            )
        else:
            self._window.array_expand_toggle_button.configure(
                text="Expand All", state="normal"
            )
        query = self._window.search_var.get().strip().lower()
        view_conflicts_only = self._window.view_conflicts_var.get()
        visible_conflict_scope = self._conflicted_tags
        if view_conflicts_only:
            self._expand_arrays_for_conflicted_tags()

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
            array_base = self._array_base_name(tag_name)
            if array_base and array_base in self._array_children_by_base:
                if array_base not in self._expanded_array_bases:
                    if not (view_conflicts_only and tag_name in visible_conflict_scope):
                        continue
            if view_conflicts_only and tag_name not in visible_conflict_scope:
                continue
            if self._active_vessel_filter and self._active_vessel_filter not in record.vessels:
                continue
            if not self._passes_program_filter(record):
                continue
            if find_text and not matches_find_scope(record, find_text, find_scope):
                continue

            find_match_count += 1
            if use_live_preview:
                row_tag, row_description = preview_map[tag_name]
            else:
                row_tag = record.tag_name
                row_description = record.description

            vessels_text = ", ".join(sorted(record.vessels))
            address_text = record_address(record)
            peers_text = ", ".join(self._tag_conflict_peers.get(tag_name, []))
            searchable = (
                f"{row_tag} {row_description} {record.proficy_name} "
                f"{record.cimplicity_pt_id} {address_text} {vessels_text} {peers_text}"
            ).lower()
            if query and query not in searchable:
                continue
            rows_to_show.append((tag_name, record))

        if view_conflicts_only:
            self._sort_column = "conflict_group"
            self._sort_descending = False

        self._sort_rows(rows_to_show)

        if len(self._tags) >= ASYNC_TABLE_THRESHOLD:
            self._refresh_generation += 1
            generation = self._refresh_generation
            snapshot = self._table_refresh_snapshot(
                rows_to_show=rows_to_show,
                preview_map=preview_map,
                use_live_preview=use_live_preview,
                find_text=find_text,
                find_scope=find_scope,
                find_match_count=find_match_count,
                preview_changes=preview_changes,
                replace_text=replace_text,
                preview_on=preview_on,
                view_conflicts_only=view_conflicts_only,
            )

            def work() -> list[dict[str, object]]:
                return self._build_table_row_payloads(snapshot)

            def on_success(payloads: list[dict[str, object]]) -> None:
                if generation != self._refresh_generation:
                    return
                self._apply_table_row_payloads(payloads, snapshot)

            self._ui_worker.submit(work, on_success)
            return

        self._render_table_rows(
            rows_to_show=rows_to_show,
            preview_map=preview_map,
            use_live_preview=use_live_preview,
            find_text=find_text,
            find_scope=find_scope,
            find_match_count=find_match_count,
            preview_changes=preview_changes,
            replace_text=replace_text,
            preview_on=preview_on,
            view_conflicts_only=view_conflicts_only,
        )


    def _table_refresh_snapshot(
        self,
        *,
        rows_to_show: list[tuple[str, TagRecord]],
        preview_map: dict[str, tuple[str, str]],
        use_live_preview: bool,
        find_text: str,
        find_scope: str,
        find_match_count: int,
        preview_changes: int,
        replace_text: str,
        preview_on: bool,
        view_conflicts_only: bool,
    ) -> dict[str, object]:
        return {
            "rows_to_show": rows_to_show,
            "preview_map": preview_map,
            "use_live_preview": use_live_preview,
            "find_text": find_text,
            "find_scope": find_scope,
            "find_match_count": find_match_count,
            "preview_changes": preview_changes,
            "replace_text": replace_text,
            "preview_on": preview_on,
            "view_conflicts_only": view_conflicts_only,
            "group_labels": dict(self._tag_mismatch_group_label),
        }


    def _build_table_row_payloads(
        self, snapshot: dict[str, object]
    ) -> list[dict[str, object]]:
        rows_to_show: list[tuple[str, TagRecord]] = snapshot["rows_to_show"]  # type: ignore[assignment]
        preview_map: dict[str, tuple[str, str]] = snapshot["preview_map"]  # type: ignore[assignment]
        use_live_preview = bool(snapshot["use_live_preview"])
        find_text = str(snapshot["find_text"])
        find_scope = str(snapshot["find_scope"])
        group_labels = snapshot["group_labels"]  # type: ignore[assignment]
        payloads: list[dict[str, object]] = []
        for row_number, (tag_name, record) in enumerate(rows_to_show, start=1):
            if use_live_preview:
                row_tag, row_description = preview_map[tag_name]
            else:
                row_tag = record.tag_name
                row_description = record.description
            row_tag = self._display_tag_label(tag_name, record)
            display_tag, display_description = format_find_replace_display(
                row_tag, row_description, find_text, find_scope, highlight=bool(find_text)
            )
            group_label = group_labels.get(tag_name, "")
            address_text = record_address(record)
            display_tag, display_description, address_text = (
                self._emphasize_matching_value(
                    tag_name, record, display_tag, display_description, address_text
                )
            )
            payloads.append(
                {
                    "iid": tag_name,
                    "row_number": row_number,
                    "values": (
                        row_number,
                        display_tag,
                        record.proficy_name or "",
                        record.cimplicity_pt_id or "",
                        display_description,
                        address_text,
                        sync_status_label(record.sync_status),
                        group_label,
                        ", ".join(sorted(record.vessels)),
                    ),
                    "style_tags": self._row_style_tags(
                        tag_name, record, group_label, bool(find_text)
                    ),
                }
            )
        return payloads


    def _row_style_tags(
        self,
        tag_name: str,
        record: TagRecord,
        group_label: str,
        find_active: bool,
    ) -> tuple[str, ...]:
        if group_label:
            digits = "".join(character for character in group_label if character.isdigit())
            index = max(int(digits or "1") - 1, 0)
            color_index = index % len(CONFLICT_GROUP_COLORS)
            return (f"conflict_g{color_index}",)
        if record.sync_status in {
            SYNC_PROFICY_DRIFT,
            SYNC_NEEDS_ALIGN,
            SYNC_NAME_MISMATCH,
        }:
            return ("sync_drift",)
        if find_active:
            return ("find_match",)
        return ()


    def _expand_arrays_for_conflicted_tags(self) -> None:
        """Expands array parents so conflicted index rows are visible in the table."""
        for tag_name in self._conflicted_tags:
            base = self._array_base_name(tag_name)
            if base and base in self._array_children_by_base:
                self._expanded_array_bases.add(base)


    def _rebuild_array_index_map(self) -> None:
        """Builds base->children map for array index tags and prunes stale expansions."""
        children: dict[str, list[str]] = {}
        for tag_name in self._tags:
            base = self._array_base_name(tag_name)
            if not base:
                continue
            children.setdefault(base, []).append(tag_name)
        for base in children:
            children[base].sort()
        self._array_children_by_base = children
        self._expanded_array_bases.intersection_update(children.keys())


    def _array_base_name(self, tag_name: str) -> str:
        match = ARRAY_INDEX_PATTERN.match(tag_name.strip().upper())
        if not match:
            return ""
        return str(match.group("base")).strip().upper()


    def _array_index_value(self, tag_name: str) -> int | None:
        match = ARRAY_INDEX_PATTERN.match(tag_name.strip().upper())
        if not match:
            return None
        return int(str(match.group("index")))


    def _is_array_parent(self, tag_name: str) -> bool:
        parent = self._tags.get(tag_name)
        if parent is None:
            return False
        if tag_name not in self._array_children_by_base:
            return False
        array_dim = str(parent.proficy_row_data.get("ArrayDimension1", "")).strip()
        return array_dim not in {"", "0"}


    def _display_tag_label(self, tag_name: str, record: TagRecord) -> str:
        base = self._array_base_name(tag_name)
        if base:
            index = self._array_index_value(tag_name)
            index_text = f"{index:03d}" if index is not None else "?"
            return f"  [{index_text}] {tag_name}"
        if self._is_array_parent(tag_name):
            child_count = len(self._array_children_by_base.get(tag_name, []))
            array_dim = str(record.proficy_row_data.get("ArrayDimension1", "")).strip()
            prefix = "▾" if tag_name in self._expanded_array_bases else "▸"
            return f"{prefix} {tag_name}  ARRAY[{array_dim}] indices:{child_count}"
        return tag_name


    def _pseudo_bold(value: str) -> str:
        """Returns a visually bold unicode variant for quick mismatch emphasis."""
        lowered = "abcdefghijklmnopqrstuvwxyz"
        uppered = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "0123456789"
        bold_lowered = "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
        bold_uppered = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
        bold_digits = "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟕𝟴𝟵"
        converted: list[str] = []
        for char in value:
            if char in lowered:
                converted.append(bold_lowered[lowered.index(char)])
            elif char in uppered:
                converted.append(bold_uppered[uppered.index(char)])
            elif char in digits:
                converted.append(bold_digits[digits.index(char)])
            else:
                converted.append(char)
        return "".join(converted)


    def _emphasize_matching_value(
        self,
        tag_name: str,
        record: TagRecord,
        display_tag: str,
        display_description: str,
        address_text: str,
    ) -> tuple[str, str, str]:
        peers = self._tag_conflict_peers.get(tag_name, [])
        description_match = False
        address_match = False
        prefix_match = False

        own_description = record.description.strip().upper()
        own_address = record_address(record).strip().upper()
        own_prefix = tag_name.strip().upper().split("_")[0]

        for peer_tag in peers:
            peer = self._tags.get(peer_tag)
            if peer is None:
                continue
            if (
                own_description
                and own_description == peer.description.strip().upper()
            ):
                description_match = True
            peer_address = record_address(peer).strip().upper()
            if own_address and own_address == peer_address:
                address_match = True
            peer_prefix = peer_tag.strip().upper().split("_")[0]
            if own_prefix and own_prefix == peer_prefix:
                prefix_match = True

        # Fallback to mismatch type if peer set is unavailable in current view.
        mismatch_type = self._tag_mismatch_type.get(tag_name, "")
        if not description_match and mismatch_type == MISMATCH_DUPLICATE_DESCRIPTION:
            description_match = True
        if not address_match and mismatch_type == MISMATCH_SHARED_ADDRESS:
            address_match = True
        if not prefix_match and mismatch_type == MISMATCH_PT_ID_PREFIX:
            prefix_match = True

        if description_match:
            display_description = self._pseudo_bold(display_description)
        if address_match:
            address_text = self._pseudo_bold(address_text)
        if prefix_match:
            display_tag = self._pseudo_bold(display_tag)
        return display_tag, display_description, address_text


    def _canonical_tag_name(self, item_id: str) -> str:
        tag_name = str(item_id).strip().upper()
        if tag_name in self._tags:
            return tag_name
        return ""


    def toggle_selected_array_indices(self) -> None:
        selected = self._get_selected_tag_names()
        if len(selected) != 1:
            messagebox.showinfo(
                "Toggle Array Indices",
                "Select exactly one array parent tag to toggle its indices.",
            )
            return
        tag_name = selected[0]
        if not self._is_array_parent(tag_name):
            messagebox.showinfo(
                "Toggle Array Indices",
                "Selected tag is not an array parent with index rows.",
            )
            return
        if tag_name in self._expanded_array_bases:
            self._expanded_array_bases.discard(tag_name)
        else:
            self._expanded_array_bases.add(tag_name)
        self.refresh_table()


    def toggle_all_array_indices(self) -> None:
        """Expands/collapses all array parent tags in one click."""
        self._rebuild_array_index_map()
        if not self._array_children_by_base:
            return
        if len(self._expanded_array_bases) >= len(self._array_children_by_base):
            self._expanded_array_bases.clear()
        else:
            self._expanded_array_bases = set(self._array_children_by_base.keys())
        self.refresh_table()


    def _apply_table_row_payloads(
        self, payloads: list[dict[str, object]], snapshot: dict[str, object]
    ) -> None:
        assert self._window.tree
        self._window.tree.delete(*self._window.tree.get_children())
        visible_labels: set[str] = set()
        for payload in payloads:
            group_label = str(payload["values"][7])  # type: ignore[index]
            if group_label:
                visible_labels.add(group_label)
            self._window.tree.insert(
                "",
                "end",
                iid=str(payload["iid"]),
                values=payload["values"],
                tags=payload["style_tags"],
            )
        visible_count = len(payloads)
        if snapshot["view_conflicts_only"]:
            self._window.status_var.set(
                f"{visible_count} internal mismatch tags in {len(visible_labels)} groups"
            )
        else:
            self._window.status_var.set(f"{visible_count} tags")
        self._window.set_find_replace_status(
            find_active=bool(snapshot["find_text"]),
            match_count=int(snapshot["find_match_count"]),
            change_count=int(snapshot["preview_changes"])
            if snapshot["replace_text"]
            else 0,
            preview_on=bool(snapshot["preview_on"]),
        )


    def _render_table_rows(
        self,
        *,
        rows_to_show: list[tuple[str, TagRecord]],
        preview_map: dict[str, tuple[str, str]],
        use_live_preview: bool,
        find_text: str,
        find_scope: str,
        find_match_count: int,
        preview_changes: int,
        replace_text: str,
        preview_on: bool,
        view_conflicts_only: bool,
    ) -> None:
        assert self._window.tree
        self._window.tree.delete(*self._window.tree.get_children())
        visible_labels: set[str] = set()

        for row_number, (tag_name, record) in enumerate(rows_to_show, start=1):
            if use_live_preview:
                row_tag, row_description = preview_map[tag_name]
            else:
                row_tag = record.tag_name
                row_description = record.description
            row_tag = self._display_tag_label(tag_name, record)

            display_tag, display_description = format_find_replace_display(
                row_tag,
                row_description,
                find_text,
                find_scope,
                highlight=bool(find_text),
            )

            group_label = self._tag_mismatch_group_label.get(tag_name, "")
            vessels_text = ", ".join(sorted(record.vessels))
            address_text = record_address(record)
            proficy_name = record.proficy_name or ""
            cimplicity_pt = record.cimplicity_pt_id or ""
            sync_label = sync_status_label(record.sync_status)
            display_tag, display_description, address_text = self._emphasize_matching_value(
                tag_name, record, display_tag, display_description, address_text
            )

            row_tags = self._row_style_tags(tag_name, record, group_label, bool(find_text))
            if group_label:
                visible_labels.add(group_label)

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
                    vessels_text,
                ),
                tags=row_tags,
            )

        visible_count = len(rows_to_show)
        if view_conflicts_only:
            if not self._conflicted_tags:
                self._window.status_var.set("No internal mismatches remain")
            else:
                self._window.status_var.set(
                    f"{visible_count} internal mismatch tags in {len(visible_labels)} groups"
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
        """Builds internal mismatch groups (description, address, prefix)."""
        result = self._mismatch_service.calculate(self._tags)
        self._conflicted_tags = result.conflicted_tags
        self._tag_conflict_peers = result.peers
        self._tag_mismatch_group_label = result.group_labels
        self._tag_mismatch_type = result.mismatch_types
        self._window.set_conflict_count(len(self._conflicted_tags))


    def _get_selected_tag_names(self) -> list[str]:
        """Returns tag names from selected rows in the tree."""
        assert self._window.tree
        selected_tags: list[str] = []
        for item_id in self._window.tree.selection():
            tag_name = str(item_id)
            if tag_name in self._tags:
                selected_tags.append(tag_name)
        return selected_tags


    def refresh_from_disk(self) -> None:
        """Reloads the current database state from disk and refreshes UI."""
        loading = LoadingDialog(self._window.root, title="Refreshing...")
        loading.show("Loading tags database from disk...")
        try:
            self._tags = self._repository.load()
            self._cross_program.review_queue.load()
            self._manual_tasks.load()
            loading.update_status("Refreshing filters and table...")
            self._refresh_filter_values()
            self._app._update_review_queue_indicator()
            self._app._update_manual_tasks_indicator()
            self.refresh_table()
        finally:
            loading.close()
        if not self._tags:
            messagebox.showwarning(
                "Database Missing or Empty",
                "No tags were loaded from disk.\n"
                "The database file may be missing or empty.",
            )

