"""Application configuration constants."""

from pathlib import Path

APP_TITLE = "Tag Central"
WINDOW_SIZE = "1240x760"
MIN_WINDOW_SIZE = (980, 620)

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_ROOT / "tags.csv"
EXPORT_FOLDER = PROJECT_ROOT / "exports"

DEFAULT_TABLE_COLUMNS = ("tag_name", "description", "vessels")
