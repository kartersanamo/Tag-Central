"""Detects internal tag mismatches by description, address, and PT_ID prefix."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app_config import MISMATCH_PREFIX_MIN_LENGTH
from models.tag_record import TagRecord
from services.address_normalizer import is_resolvable_address, normalize_address


MISMATCH_DUPLICATE_DESCRIPTION = "duplicate_description"
MISMATCH_SHARED_ADDRESS = "shared_address"
MISMATCH_PT_ID_PREFIX = "pt_id_prefix"
_ARRAY_INDEX_PATTERN = re.compile(r"^(?P<base>.+)\[(?P<index>\d+)\]$")


from models.internal_mismatch_result import InternalMismatchResult
def _tag_address(record: TagRecord) -> str:
    if record.linked_address and is_resolvable_address(record.linked_address):
        return normalize_address(record.linked_address)
    candidate = normalize_address(TagRecord._address_from_row(record.proficy_row_data))
    if is_resolvable_address(candidate):
        return candidate
    return ""


def _pt_id_prefix(tag_name: str) -> str:
    parts = tag_name.strip().upper().split("_")
    if len(parts) < 2:
        return ""
    prefix = parts[0]
    if len(prefix) < MISMATCH_PREFIX_MIN_LENGTH:
        return ""
    return prefix


def _array_base(tag_name: str) -> str:
    match = _ARRAY_INDEX_PATTERN.match(tag_name.strip().upper())
    if not match:
        return ""
    return str(match.group("base")).strip().upper()


class InternalMismatchService:
    """Builds mismatch groups for the main table and context actions."""

    def calculate(self, tags: dict[str, TagRecord]) -> InternalMismatchResult:
        result = InternalMismatchResult()
        desc_groups = self._duplicate_description_groups(tags)
        addr_groups = self._shared_address_groups(tags)
        prefix_groups = self._prefix_groups(tags, desc_groups, addr_groups)

        group_counter = {"G": 0, "A": 0, "P": 0}
        for kind, label_key, groups, mismatch_type in (
            ("G", "G", desc_groups, MISMATCH_DUPLICATE_DESCRIPTION),
            ("A", "A", addr_groups, MISMATCH_SHARED_ADDRESS),
            ("P", "P", prefix_groups, MISMATCH_PT_ID_PREFIX),
        ):
            for tag_names in groups:
                group_counter[label_key] += 1
                group_label = f"{label_key}{group_counter[label_key]}"
                sorted_tags = sorted(tag_names)
                result.conflicted_tags.update(sorted_tags)
                for tag_name in sorted_tags:
                    result.group_labels[tag_name] = group_label
                    result.mismatch_types[tag_name] = mismatch_type
                    result.peers[tag_name] = [
                        peer for peer in sorted_tags if peer != tag_name
                    ]
        return result

    @staticmethod
    def _duplicate_description_groups(
        tags: dict[str, TagRecord],
    ) -> list[set[str]]:
        descriptions: dict[str, dict[str, str]] = {}
        for tag_name, record in tags.items():
            description = record.description.strip().upper()
            if not description:
                continue
            family = _array_base(tag_name) or tag_name
            descriptions.setdefault(description, {})[family] = tag_name
        return [
            set(families.values())
            for families in descriptions.values()
            if len(families) > 1
        ]

    @staticmethod
    def _shared_address_groups(tags: dict[str, TagRecord]) -> list[set[str]]:
        addresses: dict[str, dict[str, str]] = {}
        for tag_name, record in tags.items():
            address = _tag_address(record)
            if not address:
                continue
            family = _array_base(tag_name) or tag_name
            addresses.setdefault(address, {})[family] = tag_name
        groups: list[set[str]] = []
        for family_map in addresses.values():
            tag_names = list(family_map.values())
            if len(tag_names) <= 1:
                continue
            descriptions = {tags[name].description.strip().upper() for name in tag_names}
            if len(descriptions) > 1:
                groups.append(set(tag_names))
        return groups

    @staticmethod
    def _prefix_groups(
        tags: dict[str, TagRecord],
        desc_groups: list[set[str]],
        addr_groups: list[set[str]],
    ) -> list[set[str]]:
        already_grouped: set[str] = set()
        for group in desc_groups + addr_groups:
            already_grouped.update(group)

        buckets: dict[tuple[str, str], list[str]] = {}
        for tag_name, record in tags.items():
            if tag_name in already_grouped:
                continue
            if _array_base(tag_name):
                continue
            prefix = _pt_id_prefix(tag_name)
            address = _tag_address(record)
            if not prefix or not address:
                continue
            buckets.setdefault((prefix, address), []).append(tag_name)

        groups: list[set[str]] = []
        for tag_names in buckets.values():
            if len(tag_names) > 1:
                groups.append(set(tag_names))
        return groups
