"""Configurable tag-name alias expansion for cross-program linking."""

from __future__ import annotations

import json
from pathlib import Path

from app_config import ALIAS_RULES_FILE


class TagAliasRules:
    """Loads prefix replacement rules from alias_rules.json."""

    def __init__(self, rules_file: Path | None = None) -> None:
        self._rules_file = rules_file or ALIAS_RULES_FILE
        self._prefix_pairs: list[tuple[str, str]] = []
        self._load()

    def _load(self) -> None:
        if not self._rules_file.exists():
            self._prefix_pairs = [("ALM_", "ALARM_"), ("ALARM_", "ALM_")]
            return
        try:
            payload = json.loads(self._rules_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._prefix_pairs = [("ALM_", "ALARM_"), ("ALARM_", "ALM_")]
            return

        pairs: list[tuple[str, str]] = []
        for item in payload.get("prefix_pairs", []):
            if not isinstance(item, dict):
                continue
            source = str(item.get("from", "")).strip().upper()
            target = str(item.get("to", "")).strip().upper()
            if source and target:
                pairs.append((source, target))
        self._prefix_pairs = pairs or [("ALM_", "ALARM_"), ("ALARM_", "ALM_")]

    def expand(self, tag_name: str) -> set[str]:
        """Returns the tag and alias variants for matching."""
        normalized = tag_name.strip().upper()
        variants = {normalized}
        for source, target in self._prefix_pairs:
            if normalized.startswith(source):
                variants.add(target + normalized[len(source) :])
            if normalized.startswith(target):
                variants.add(source + normalized[len(target) :])
        return variants
