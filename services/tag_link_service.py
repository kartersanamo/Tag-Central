"""Links Cimplicity import rows to canonical tag records."""

from __future__ import annotations

from models.link_result import LinkResult, LinkMethod
from models.tag_record import TagRecord
from services.address_normalizer import (
    addresses_equivalent,
    is_resolvable_address,
    normalize_address,
)
from services.debug_logger import debug_logger
from services.tag_alias_rules import TagAliasRules


class TagLinkService:
    """Matches imported Cimplicity rows to existing canonical records."""

    def __init__(self, alias_rules: TagAliasRules | None = None) -> None:
        self._aliases = alias_rules or TagAliasRules()

    def link_cimplicity_row(
        self,
        tags: dict[str, TagRecord],
        pt_id: str,
        address: str,
    ) -> LinkResult:
        """Finds the best canonical tag for a Cimplicity PT_ID and ADDR."""
        pt_id = pt_id.strip().upper()
        normalized_address = normalize_address(address)
        debug_logger.log(
            "linking",
            "Link Cimplicity row",
            pt_id=pt_id,
            raw_address=address,
            normalized_address=normalized_address,
            tag_count=len(tags),
        )

        if pt_id in tags:
            debug_logger.log(
                "linking", "Matched by exact PT_ID", pt_id=pt_id, canonical_tag=pt_id
            )
            return LinkResult(canonical_tag=pt_id, method="exact_id", ambiguous_tags=[])

        for tag_name, record in tags.items():
            if record.cimplicity_pt_id == pt_id:
                debug_logger.log(
                    "linking",
                    "Matched by stored Cimplicity PT_ID",
                    pt_id=pt_id,
                    canonical_tag=tag_name,
                )
                return LinkResult(canonical_tag=tag_name, method="cimplicity_pt_id", ambiguous_tags=[])

        if is_resolvable_address(normalized_address):
            address_matches = self._tags_by_address(tags, normalized_address)
            if len(address_matches) == 1:
                debug_logger.log(
                    "linking",
                    "Matched by address",
                    pt_id=pt_id,
                    normalized_address=normalized_address,
                    canonical_tag=address_matches[0],
                )
                return LinkResult(
                    canonical_tag=address_matches[0],
                    method="address",
                    ambiguous_tags=[],
                )
            if len(address_matches) > 1:
                debug_logger.log(
                    "ambiguous_address",
                    "Ambiguous address match",
                    pt_id=pt_id,
                    normalized_address=normalized_address,
                    candidate_tags=address_matches,
                )
                return LinkResult(
                    canonical_tag=None,
                    method=None,
                    ambiguous_tags=address_matches,
                )

        if is_resolvable_address(normalized_address):
            for variant in self._aliases.expand(pt_id):
                if variant in tags:
                    record = tags[variant]
                    record_address = normalize_address(
                        TagRecord._address_from_row(record.proficy_row_data)
                    )
                    if addresses_equivalent(record_address, normalized_address):
                        debug_logger.log(
                            "linking",
                            "Matched by alias + address",
                            pt_id=pt_id,
                            alias_variant=variant,
                            canonical_tag=variant,
                            normalized_address=normalized_address,
                        )
                        return LinkResult(
                            canonical_tag=variant,
                            method="alias",
                            ambiguous_tags=[],
                        )

        debug_logger.log(
            "linking",
            "No match for Cimplicity row",
            pt_id=pt_id,
            normalized_address=normalized_address,
        )
        return LinkResult(canonical_tag=None, method=None, ambiguous_tags=[])

    @staticmethod
    def _tags_by_address(tags: dict[str, TagRecord], address: str) -> list[str]:
        matches: list[str] = []
        for tag_name, record in tags.items():
            record_address = record.linked_address or normalize_address(
                TagRecord._address_from_row(record.proficy_row_data)
            )
            if addresses_equivalent(record_address, address):
                matches.append(tag_name)
        return matches

    def build_address_index(self, tags: dict[str, TagRecord]) -> dict[str, list[str]]:
        """Maps normalized address to canonical tag names."""
        index: dict[str, list[str]] = {}
        for tag_name, record in tags.items():
            address = record.linked_address or normalize_address(
                TagRecord._address_from_row(record.proficy_row_data)
            )
            if not address:
                continue
            index.setdefault(address, []).append(tag_name)
        return index
