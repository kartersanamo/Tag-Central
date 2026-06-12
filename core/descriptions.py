"""Fill missing import descriptions without GUI dialogs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from core.exceptions import PolicyAbortError

if TYPE_CHECKING:
    from core.tag_central_app import TagCentralApp


def fill_missing_descriptions_for_field(
    app: TagCentralApp,
    *,
    rows: list[dict[str, str]],
    summary: dict[str, int],
    tag_field: str,
    description_field: str,
    descriptions_mode: str,
    on_apply: Callable[[str, str, str, int], None] | None = None,
) -> bool:
    """Auto-fills or rejects rows with empty descriptions."""
    used_descriptions: set[str] = {
        record.description.strip().upper()
        for record in app.tags.values()
        if record.description.strip()
    }
    for row_data in rows:
        existing_description = row_data.get(description_field, "").strip().upper()
        if existing_description:
            used_descriptions.add(existing_description)

    candidates: list[tuple[int, str, str]] = []
    for index, row_data in enumerate(rows):
        tag_name = row_data.get(tag_field, "").strip().upper()
        description = row_data.get(description_field, "").strip().upper()
        if tag_name and not description:
            suggestion = app.suggester.suggest_unique(tag_name, used_descriptions)
            candidates.append((index, tag_name, suggestion))

    if not candidates:
        return True

    if descriptions_mode == "fail":
        missing = ", ".join(tag for _, tag, _ in candidates[:8])
        suffix = "..." if len(candidates) > 8 else ""
        raise PolicyAbortError(
            f"{len(candidates)} row(s) missing {description_field}: {missing}{suffix}"
        )

    for row_index, tag_name, suggestion in candidates:
        row_data = rows[row_index]
        old_value = str(row_data.get(description_field, "")).strip().upper()
        row_data[description_field] = suggestion
        used_descriptions.add(suggestion)
        summary["rows_missing_description_filled"] += 1
        if on_apply is not None:
            on_apply(tag_name, old_value, suggestion, row_index)

    return True
