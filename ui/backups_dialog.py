"""Backup management window."""

from __future__ import annotations

import tkinter as tk
from typing import Callable
from tkinter import messagebox, simpledialog, ttk

from services.backup_service import BackupService


class BackupsDialog:
    """Displays backups with preview, restore, rename, and delete actions."""

    def __init__(
        self,
        parent: tk.Tk,
        backup_service: BackupService,
        on_restore: Callable[[str], bool],
        on_revert_latest: Callable[[], bool],
    ) -> None:
        self._backup_service = backup_service
        self._on_restore = on_restore
        self._on_revert_latest = on_revert_latest

        self._window = tk.Toplevel(parent)
        self._window.title("Backups")
        self._window.geometry("1100x720")
        self._window.transient(parent)
        self._window.grab_set()

        self._build_ui()
        self._refresh_list()

    def show(self) -> None:
        """Shows dialog modally."""
        self._window.wait_window()

    def _build_ui(self) -> None:
        header = ttk.Frame(self._window, padding=14)
        header.pack(fill="x")
        ttk.Label(header, text="Backups", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Manage database snapshots. Loading a backup replaces current data. "
                "A temporary pre-load backup is saved automatically."
            ),
        ).pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(self._window, padding=(14, 0, 14, 10))
        actions.pack(fill="x")
        ttk.Button(actions, text="Create Backup Now", command=self._create_backup_now).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Load Selected Backup", command=self._load_selected).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Rename Selected", command=self._rename_selected).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Delete Selected", command=self._delete_selected).pack(
            side="left", padx=8
        )
        ttk.Button(
            actions,
            text="Revert Latest Backup",
            command=self._revert_latest,
        ).pack(side="left", padx=(18, 8))
        ttk.Button(actions, text="Refresh", command=self._refresh_list).pack(
            side="right", padx=(0, 8)
        )
        ttk.Button(actions, text="Close", command=self._window.destroy).pack(side="right")

        body = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._tree = ttk.Treeview(
            left,
            columns=("name", "rows", "size_kb", "modified"),
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("name", text="Backup")
        self._tree.heading("rows", text="Rows")
        self._tree.heading("size_kb", text="Size (KB)")
        self._tree.heading("modified", text="Modified")
        self._tree.column("name", width=280, anchor="w")
        self._tree.column("rows", width=70, anchor="center")
        self._tree.column("size_kb", width=90, anchor="center")
        self._tree.column("modified", width=180, anchor="w")
        scroll = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self._tree.bind("<<TreeviewSelect>>", lambda *_: self._refresh_preview())

        ttk.Label(right, text="Preview", font=("Helvetica", 12, "bold")).pack(anchor="w")
        self._preview = tk.Text(right, wrap="none", height=30)
        self._preview.pack(fill="both", expand=True)

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
