"""Backup management window."""

from __future__ import annotations

import tkinter as tk
from typing import Callable
from tkinter import messagebox, simpledialog

import customtkinter as ctk

from services.backup_service import BackupService
from ui.ctk_theme import FONT_BODY, FONT_TITLE, button_accent_kwargs, button_neutral_kwargs
from ui.ctk_tree import create_data_treeview


class BackupsDialog:
    """Displays backups with preview, restore, rename, and delete actions."""

    def __init__(
        self,
        parent: ctk.CTk,
        backup_service: BackupService,
        on_restore: Callable[[str], bool],
        on_revert_latest: Callable[[], bool],
    ) -> None:
        self._backup_service = backup_service
        self._on_restore = on_restore
        self._on_revert_latest = on_revert_latest

        self._window = ctk.CTkToplevel(parent)
        self._window.title("Backups")
        self._window.geometry("1100x720")
        self._window.transient(parent)
        self._window.grab_set()

        self._build_ui()
        self._refresh_list()

    def show(self) -> None:
        self._window.wait_window()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self._window, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(header, text="Backups", font=FONT_TITLE, anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=(
                "Manage database snapshots. Loading a backup replaces current data. "
                "A temporary pre-load backup is saved automatically."
            ),
            font=FONT_BODY,
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        actions = ctk.CTkFrame(self._window, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkButton(
            actions,
            text="Create Backup Now",
            command=self._create_backup_now,
            **button_accent_kwargs(),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Load Selected Backup",
            command=self._load_selected,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            actions,
            text="Rename Selected",
            command=self._rename_selected,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            actions,
            text="Delete Selected",
            command=self._delete_selected,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            actions,
            text="Revert Latest Backup",
            command=self._revert_latest,
            **button_neutral_kwargs(),
        ).pack(side="left", padx=(18, 8))
        ctk.CTkButton(
            actions, text="Refresh", command=self._refresh_list, **button_neutral_kwargs()
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            actions, text="Close", command=self._window.destroy, **button_neutral_kwargs()
        ).pack(side="right")

        body = ctk.CTkFrame(self._window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        left = ctk.CTkFrame(body)
        right = ctk.CTkFrame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._tree, _scroll = create_data_treeview(
            left,
            ("name", "rows", "size_kb", "modified"),
            {
                "name": "Backup",
                "rows": "Rows",
                "size_kb": "Size (KB)",
                "modified": "Modified",
            },
            {"name": 280, "rows": 70, "size_kb": 90, "modified": 180},
            height=20,
        )
        self._tree.configure(selectmode="browse")
        self._tree.bind("<<TreeviewSelect>>", lambda *_: self._refresh_preview())

        ctk.CTkLabel(
            right, text="Preview", font=(FONT_BODY[0], FONT_BODY[1], "bold"), anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 6))
        self._preview = ctk.CTkTextbox(right, height=500)
        self._preview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _refresh_list(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for item in self._backup_service.list_backups():
            self._tree.insert(
                "",
                "end",
                iid=str(item["name"]),
                values=(
                    item["name"],
                    item["rows"],
                    item["size_kb"],
                    item["modified"],
                ),
            )
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._refresh_preview()
        else:
            self._preview.delete("1.0", "end")
            self._preview.insert("1.0", "No backups available.")

    def _selected_backup(self) -> str | None:
        selection = self._tree.selection()
        return str(selection[0]) if selection else None

    def _refresh_preview(self) -> None:
        name = self._selected_backup()
        self._preview.delete("1.0", "end")
        if not name:
            self._preview.insert("1.0", "Select a backup to preview.")
            return
        try:
            preview = self._backup_service.preview_backup(name, limit=20)
        except FileNotFoundError:
            self._preview.insert("1.0", "Backup no longer exists.")
            return

        rows = preview["rows"]
        total_rows = preview["total_rows"]
        if not rows:
            self._preview.insert("1.0", f"{name}\n\nRows: {total_rows}\n\nNo row data.")
            return

        first = rows[0]
        headers = list(first.keys())
        lines = [f"{name}", f"Rows: {total_rows}", "", ",".join(headers)]
        for row in rows:
            lines.append(",".join(str(row.get(header, "")) for header in headers))
        if total_rows > len(rows):
            lines.append(f"... ({total_rows - len(rows)} more rows)")
        self._preview.insert("1.0", "\n".join(lines))

    def _create_backup_now(self) -> None:
        path = self._backup_service.create_backup_from_database(prefix="manual")
        if path is None:
            messagebox.showwarning("No Data", "No database file exists to back up.")
            return
        self._refresh_list()
        messagebox.showinfo("Backup Created", f"Created backup: {path.name}")

    def _load_selected(self) -> None:
        name = self._selected_backup()
        if not name:
            messagebox.showinfo("Selection Required", "Select a backup to load.")
            return
        confirmed = messagebox.askyesno(
            "Load Backup - Important",
            "This will WIPE all current data and replace it with the selected backup.\n\n"
            "A temporary pre-load backup will be saved first.\n\n"
            "Continue?",
        )
        if not confirmed:
            return
        success = self._on_restore(name)
        if success:
            messagebox.showinfo("Backup Loaded", f"Loaded backup: {name}")
            self._refresh_list()

    def _rename_selected(self) -> None:
        name = self._selected_backup()
        if not name:
            messagebox.showinfo("Selection Required", "Select a backup to rename.")
            return
        new_name = simpledialog.askstring("Rename Backup", "New backup name:", initialvalue=name)
        if not new_name:
            return
        try:
            updated = self._backup_service.rename_backup(name, new_name)
        except (FileNotFoundError, ValueError, FileExistsError) as error:
            messagebox.showerror("Rename Error", str(error))
            return
        self._refresh_list()
        self._tree.selection_set(str(updated.name))

    def _delete_selected(self) -> None:
        name = self._selected_backup()
        if not name:
            messagebox.showinfo("Selection Required", "Select a backup to delete.")
            return
        confirmed = messagebox.askyesno(
            "Delete Backup",
            f"Delete backup '{name}'?\n\nThis cannot be undone.",
        )
        if not confirmed:
            return
        self._backup_service.delete_backup(name)
        self._refresh_list()

    def _revert_latest(self) -> None:
        confirmed = messagebox.askyesno(
            "Revert Latest Backup",
            "Revert to the temporary pre-load backup?\n\n"
            "This will replace current data.",
        )
        if not confirmed:
            return
        success = self._on_revert_latest()
        if success:
            messagebox.showinfo("Reverted", "Latest pre-load backup restored.")
            self._refresh_list()
        else:
            messagebox.showwarning("No Pre-load Backup", "No temporary backup is available.")
