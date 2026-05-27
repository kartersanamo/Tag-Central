"""Suggests human-readable descriptions from tag names."""

from __future__ import annotations

import re


class DescriptionSuggester:
    """Generates description suggestions using common tag conventions."""

    _TOKEN_MAP = {
        "BS": "BALLAST",
        "FW": "FRESH WATER",
        "SW": "SEA WATER",
        "FO": "FUEL OIL",
        "DO": "DIESEL OIL",
        "LO": "LUBE OIL",
        "TK": "TANK",
        "TANK": "TANK",
        "GRAVITY": "GRAVITY",
        "INCH": "INCHES",
        "INCHES": "INCHES",
        "LEVEL": "VOLUME",
        "MAX": "MAX",
        "VOL": "VOL",
        "PERCENT": "PERCENTAGE",
        "PCT": "PERCENTAGE",
        "TEMP": "TEMPERATURE",
        "PRESS": "PRESSURE",
        "FLOW": "FLOW",
        "RPM": "RPM",
    }

    def suggest(self, tag_name: str) -> str:
        """Returns a best-effort description for a tag."""
        cleaned_tag = tag_name.strip().upper()
        if not cleaned_tag:
            return ""

        parts = [part for part in cleaned_tag.split("_") if part]
        mapped_parts = [self._map_token(part) for part in parts]
        text = " ".join(part for part in mapped_parts if part).strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def suggest_unique(self, tag_name: str, used_descriptions: set[str]) -> str:
        """
        Returns a unique suggestion not already present in `used_descriptions`.
        Uses a number from the tag at the end when de-duplicating.
        """
        suggested = self.suggest(tag_name).strip().upper() or tag_name.strip().upper()
        base = re.sub(r"\s+#\d+$", "", suggested).strip() or suggested
        normalized_used = {value.strip().upper() for value in used_descriptions if value.strip()}
        if base not in normalized_used:
            used_descriptions.add(base)
            return base

        number_hint = self._number_hint(tag_name)
        if number_hint:
            candidate = f"{base} {number_hint}"
            if candidate not in normalized_used:
                used_descriptions.add(candidate)
                return candidate

        index = 2
        while True:
            if number_hint:
                candidate = f"{base} {number_hint}-{index}"
            else:
                candidate = f"{base} {index}"
            if candidate not in normalized_used:
                used_descriptions.add(candidate)
                return candidate
            index += 1

    def _map_token(self, token: str) -> str:
        if token in self._TOKEN_MAP:
            return self._TOKEN_MAP[token]

        ballast_match = re.fullmatch(r"(\d+)([PS])([A-Z])?", token)
        if ballast_match:
            number, side, section = ballast_match.groups()
            value = f"#{number}-{side}"
            if section:
                value = f"{value}-{section}"
            return value

        side_match = re.fullmatch(r"(\d+)([PS])", token)
        if side_match:
            number, side = side_match.groups()
            return f"#{number}-{side}"

        number_match = re.fullmatch(r"\d+", token)
        if number_match:
            return f"#{token}"

        if len(token) == 1 and token.isalpha():
            return token

        return token.replace("-", " ")

    @staticmethod
    def _number_hint(tag_name: str) -> str:
        numbers = re.findall(r"\d+", tag_name.strip().upper())
        return numbers[-1] if numbers else ""
