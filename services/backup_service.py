"""Backup management for tag database snapshots."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path


class BackupService:
    """Creates, lists, previews, and restores CSV backups."""

    PRELOAD_FILENAME = "__LATEST_PRELOAD__.csv"

    def __init__(self, backup_folder: Path, database_file: Path) -> None:
        self._backup_folder = backup_folder
        self._database_file = database_file
        self._backup_folder.mkdir(parents=True, exist_ok=True)

    def list_backups(self) -> list[dict[str, object]]:
        """Returns backup metadata for display."""
        backups: list[dict[str, object]] = []
        for path in sorted(
            self._backup_folder.glob("*.csv"),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        ):
            if path.name == self.PRELOAD_FILENAME:
                continue
            stat = path.stat()
            backups.append(
                {
                    "name": path.name,
                    "path": path,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "size_kb": round(stat.st_size / 1024, 1),
                    "rows": self._count_rows(path),
                }
            )
        return backups

    def create_backup_from_database(self, prefix: str = "backup") -> Path | None:
        """Creates a timestamped backup from current database file."""
        if not self._database_file.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self._backup_folder / f"{prefix}_{timestamp}.csv"
        shutil.copy2(self._database_file, destination)
        return destination

    def create_preload_backup(self) -> Path | None:
        """Creates/overwrites temporary revert backup before restore."""
        if not self._database_file.exists():
            return None
        destination = self._backup_folder / self.PRELOAD_FILENAME
        shutil.copy2(self._database_file, destination)
        return destination

    def has_preload_backup(self) -> bool:
        """Returns True when a revert backup is available."""
        return (self._backup_folder / self.PRELOAD_FILENAME).exists()

    def restore_preload_backup(self) -> bool:
        """Restores database from temporary revert backup."""
        source = self._backup_folder / self.PRELOAD_FILENAME
        if not source.exists():
            return False
        shutil.copy2(source, self._database_file)
        return True

    def restore_backup(self, backup_name: str) -> Path:
        """Restores a named backup to tags database."""
        source = self._backup_folder / backup_name
        if not source.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")
        shutil.copy2(source, self._database_file)
        return source

    def rename_backup(self, old_name: str, new_name: str) -> Path:
        """Renames backup file."""
        source = self._backup_folder / old_name
        if not source.exists():
            raise FileNotFoundError(f"Backup not found: {old_name}")
        normalized = new_name.strip()
        if not normalized:
            raise ValueError("Backup name cannot be empty.")
        if not normalized.lower().endswith(".csv"):
            normalized += ".csv"
        destination = self._backup_folder / normalized
        if destination.exists():
            raise FileExistsError(f"Backup already exists: {destination.name}")
        source.rename(destination)
        return destination

    def delete_backup(self, name: str) -> None:
        """Deletes a named backup file."""
        path = self._backup_folder / name
        if path.exists():
            path.unlink()

    def preview_backup(self, backup_name: str, limit: int = 20) -> dict[str, object]:
        """Reads a small preview of backup CSV content."""
        path = self._backup_folder / backup_name
        if not path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = []
            for index, row in enumerate(reader):
                if index >= limit:
                    break
                rows.append(row)
        return {"rows": rows, "total_rows": self._count_rows(path)}

    @staticmethod
    def _count_rows(path: Path) -> int:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader, None)
            return sum(1 for _ in reader)
