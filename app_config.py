"""Application configuration constants."""

from pathlib import Path

APP_TITLE = "Tag Central"
WINDOW_SIZE = "1480x760"
MIN_WINDOW_SIZE = (1100, 620)

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_ROOT / "tags.csv"
EXPORT_FOLDER = PROJECT_ROOT / "exports"
BACKUP_FOLDER = PROJECT_ROOT / "backups"
ALIAS_RULES_FILE = PROJECT_ROOT / "alias_rules.json"
CIMPLICITY_REVIEW_QUEUE_FILE = PROJECT_ROOT / "cimplicity_review_queue.json"
CIMPLICITY_MANUAL_REPORT_FILE = PROJECT_ROOT / "cimplicity_manual_report.json"
CIMPLICITY_MANUAL_TASKS_FILE = PROJECT_ROOT / "cimplicity_manual_tasks.json"

DEFAULT_TABLE_COLUMNS = (
    "row_number",
    "tag_name",
    "proficy_name",
    "cimplicity_pt_id",
    "description",
    "address",
    "sync_status",
    "conflict_group",
    "conflicts_with",
    "vessels",
)

SYNC_STATUS_LABELS = {
    "synced": "Synced",
    "proficy_only": "Proficy Only",
    "proficy_drift": "Proficy Drift",
    "name_mismatch": "Name Mismatch",
    "needs_align": "Needs Align",
    "cimplicity_linked": "Cimplicity Linked",
}

PROGRAM_FILTER_VALUES = ("ALL", "Proficy only", "Cimplicity only", "Needs sync")

CONFLICT_GROUP_COLORS = (
    "#ffe8e8",
    "#fff3e0",
    "#fff9e6",
    "#e8f5e9",
    "#e3f2fd",
    "#f3e5f5",
    "#fce4ec",
    "#e0f7fa",
)
