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

MISMATCH_PREFIX_MIN_LENGTH = 6
ASYNC_TABLE_THRESHOLD = 500
BULK_DELETE_BACKUP_THRESHOLD = 5
BULK_IMPORT_BACKUP_THRESHOLD = 100
PERSIST_DEBOUNCE_MS = 300

# Debug logging controls.
# Master switch must be True for any debug output to print.
DEBUG_LOGGING_ENABLED = False
DEBUG_LOGGING_OPTIONS = {
    # High-level pipeline stages and summary counts.
    "import_flow": True,
    # Detailed link attempts and match method decisions.
    "linking": True,
    # Ambiguous address rows with all candidate tags and addresses.
    "ambiguous_address": True,
    # Queueing/exports and conflict decisions.
    "export_queue": False,
    "conflicts": False,
}

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
