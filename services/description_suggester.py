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
