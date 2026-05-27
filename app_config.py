"""Application configuration constants."""

from pathlib import Path

APP_TITLE = "Tag Central"
WINDOW_SIZE = "1240x760"
MIN_WINDOW_SIZE = (980, 620)

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_ROOT / "tags.csv"
EXPORT_FOLDER = PROJECT_ROOT / "exports"
BACKUP_FOLDER = PROJECT_ROOT / "backups"

DEFAULT_TABLE_COLUMNS = (
    "row_number",
    "tag_name",
    "description",
    "address",
    "conflict_group",
    "conflicts_with",
    "vessels",
)

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
