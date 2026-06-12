"""Human-readable sync status labels for UI display."""

from app_config import SYNC_STATUS_LABELS


def sync_status_label(status: str) -> str:
    return SYNC_STATUS_LABELS.get(status, status.replace("_", " ").title())
