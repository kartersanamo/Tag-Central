"""Shared mutable application state and service instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import tkinter as tk

from app_config import (
    BACKUP_FOLDER,
    DATABASE_FILE,
    EXPORT_FOLDER,
    PERSIST_DEBOUNCE_MS,
)
from services.backup_service import BackupService
from services.cimplicity_change_report import CimplicityChangeReport
from services.cimplicity_loader import CimplicityLoader
from services.cimplicity_manual_tasks import CimplicityManualTasks
from services.cross_program_sync_service import CrossProgramSyncService
from services.description_suggester import DescriptionSuggester
from services.documentation_service import DocumentationService
from services.export_queue_service import ExportQueueService
from services.export_service import ExportService
from services.export_validation_service import ExportValidationService
from services.internal_mismatch_service import InternalMismatchService
from services.proficy_import_analyzer import ProficyImportAnalyzer
from services.spreadsheet_loader import SpreadsheetLoader
from services.sync_status_labels import sync_status_label
from services.tag_merge_service import TagMergeService
from services.tag_repository import TagRepository
from services.tag_sync_service import TagSyncService
from services.ui_worker import UiWorker

if TYPE_CHECKING:
    from models.tag_record import TagRecord
    from ui.main_window import MainWindow


@dataclass
class AppContext:
    """Holds all shared mutable state and service instances for controllers."""

    root: tk.Tk | None = None
    headless: bool = False
    repository: TagRepository = field(
        default_factory=lambda: TagRepository(DATABASE_FILE)
    )
    loader: SpreadsheetLoader = field(default_factory=SpreadsheetLoader)
    cimplicity_loader: CimplicityLoader = field(default_factory=CimplicityLoader)
    suggester: DescriptionSuggester = field(default_factory=DescriptionSuggester)
    export_service: ExportService = field(
        default_factory=lambda: ExportService(EXPORT_FOLDER)
    )
    backup_service: BackupService = field(
        default_factory=lambda: BackupService(BACKUP_FOLDER, DATABASE_FILE)
    )
    sync: TagSyncService = field(default_factory=TagSyncService)
    cross_program: CrossProgramSyncService = field(
        default_factory=CrossProgramSyncService
    )
    cimplicity_report: CimplicityChangeReport = field(
        default_factory=CimplicityChangeReport
    )
    manual_tasks: CimplicityManualTasks = field(default_factory=CimplicityManualTasks)
    cimplicity_manual_entries: list[dict[str, str]] = field(default_factory=list)
    tags: dict[str, TagRecord] = field(default_factory=dict)
    active_vessel_filter: str | None = None
    conflicted_tags: set[str] = field(default_factory=set)
    tag_conflict_peers: dict[str, list[str]] = field(default_factory=dict)
    tag_mismatch_group_label: dict[str, str] = field(default_factory=dict)
    tag_mismatch_type: dict[str, str] = field(default_factory=dict)
    export_queue: ExportQueueService = field(default_factory=ExportQueueService)
    export_validator: ExportValidationService = field(
        default_factory=ExportValidationService
    )
    mismatch_service: InternalMismatchService = field(
        default_factory=InternalMismatchService
    )
    merge_service: TagMergeService = field(default_factory=TagMergeService)
    documentation: DocumentationService | None = None
    ui_worker: UiWorker | None = None
    persist_after_id: str | None = None
    refresh_generation: int = 0
    last_cimplicity_link_report: list[str] = field(default_factory=list)
    sort_column: str = "tag_name"
    sort_descending: bool = False
    sort_before_internal_mismatches: tuple[str, bool] | None = None
    array_children_by_base: dict[str, list[str]] = field(default_factory=dict)
    expanded_array_bases: set[str] = field(default_factory=set)
    column_heading_labels: dict[str, str] = field(
        default_factory=lambda: {
            "row_number": "#",
            "tag_name": "Tag",
            "proficy_name": "Proficy Name",
            "cimplicity_pt_id": "Cimplicity PT_ID",
            "description": "Description",
            "address": "Address",
            "sync_status": "Sync",
            "conflict_group": "Group",
            "vessels": "Vessels",
        }
    )
    window: MainWindow | None = None
    proficy_analyzer: ProficyImportAnalyzer | None = None

    def __post_init__(self) -> None:
        if not self.tags:
            self.tags = self.repository.load()
        if self.proficy_analyzer is None:
            self.proficy_analyzer = ProficyImportAnalyzer(self.sync)
        if self.documentation is None:
            self.documentation = DocumentationService(
                sync_status_label=sync_status_label
            )
        if self.ui_worker is None and not self.headless and self.root is not None:
            self.ui_worker = UiWorker(self.root)

    @classmethod
    def create_headless(cls) -> AppContext:
        """Factory for CLI and other non-GUI entry points."""
        return cls(root=None, headless=True)

    def persist_tags(self) -> None:
        """Persists current in-memory table to tags.csv."""
        if self.persist_after_id is not None and self.window is not None:
            self.window.root.after_cancel(self.persist_after_id)
            self.persist_after_id = None
        self.repository.save(self.tags)

    def schedule_persist(self) -> None:
        """Debounces database writes during rapid bulk edits."""
        if self.window is None:
            self.persist_tags()
            return
        if self.persist_after_id is not None:
            self.window.root.after_cancel(self.persist_after_id)
        self.persist_after_id = self.window.root.after(
            PERSIST_DEBOUNCE_MS, self.flush_scheduled_persist
        )

    def flush_scheduled_persist(self) -> None:
        self.persist_after_id = None
        self.repository.save(self.tags)
