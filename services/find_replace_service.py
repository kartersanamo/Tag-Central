"""Find/replace helper functions for tag table display and apply logic."""

from __future__ import annotations

import re

from models.tag_record import TagRecord


def preview_replace(source: str, pattern: re.Pattern[str], replace_text: str) -> str:
    return pattern.sub(replace_text.upper(), source).strip().upper()


def matches_find_scope(record: TagRecord, find_text: str, scope: str) -> bool:
    """True when find_text appears in the selected scope fields."""
    query = find_text.lower()
    if scope in {"tag", "both"} and query in record.tag_name.lower():
        return True
    if scope in {"description", "both"} and query in record.description.lower():
        return True
    return False


def highlight_find_text(text: str, find_text: str) -> str:
    """Wraps case-insensitive find matches with highlight markers for display."""
    if not find_text:
        return text
    pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)
    parts: list[str] = []
    last_index = 0
    for match in pattern.finditer(text):
        parts.append(text[last_index : match.start()])
        parts.append(f"[{match.group()}]")
        last_index = match.end()
    parts.append(text[last_index:])
    return "".join(parts)


def format_find_replace_display(
    tag_text: str,
    description_text: str,
    find_text: str,
    scope: str,
    highlight: bool,
) -> tuple[str, str]:
    """Applies find-match highlighting to scoped columns when requested."""
    if not highlight or not find_text:
        return tag_text, description_text
    display_tag = tag_text
    display_description = description_text
    if scope in {"tag", "both"}:
        display_tag = highlight_find_text(tag_text, find_text)
    if scope in {"description", "both"}:
        display_description = highlight_find_text(description_text, find_text)
    return display_tag, display_description
