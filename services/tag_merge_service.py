"""Merge two canonical tags into one survivor record."""

from __future__ import annotations

from models.tag_record import SYNC_SYNCED, TagRecord
from services.address_normalizer import is_resolvable_address


class TagMergeService:
    """Combines two tag records; Cimplicity-linked data wins when present."""

    def merge_tags(
        self,
        tags: dict[str, TagRecord],
        primary: str,
        secondary: str,
    ) -> TagRecord:
        primary_key = primary.strip().upper()
        secondary_key = secondary.strip().upper()
        if primary_key not in tags or secondary_key not in tags:
            raise KeyError("Both tags must exist to merge.")
        if primary_key == secondary_key:
            return tags[primary_key]

        survivor = tags[primary_key]
        other = tags[secondary_key]

        survivor.vessels |= other.vessels
        if other.cimplicity_pt_id and not survivor.cimplicity_pt_id:
            survivor.cimplicity_row_data = dict(other.cimplicity_row_data)
            survivor.cimplicity_pt_id = other.cimplicity_pt_id
            survivor.link_method = other.link_method or survivor.link_method

        if (
            other.linked_address
            and not survivor.linked_address
            and is_resolvable_address(other.linked_address)
        ):
            survivor.linked_address = other.linked_address

        if other.proficy_row_data and not survivor.proficy_row_data:
            survivor.proficy_row_data = dict(other.proficy_row_data)
            survivor.proficy_name = other.proficy_name or survivor.proficy_name

        if survivor.cimplicity_pt_id:
            survivor.sync_status = SYNC_SYNCED
        elif survivor.proficy_row_data:
            survivor.sync_status = other.sync_status

        tags.pop(secondary_key)
        survivor.tag_name = primary_key
        tags[primary_key] = survivor
        return survivor
