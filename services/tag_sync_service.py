"""Business logic for tag synchronization."""

from __future__ import annotations

from models.tag_record import TagRecord


class TagSyncService:
    """Handles import merge and mutation operations."""

    def find_conflict(
        self,
        tags: dict[str, TagRecord],
        imported_tag: str,
        imported_description: str,
    ) -> tuple[str, TagRecord] | None:
        """Returns the first conflicting record, if any."""
        for existing_tag, record in tags.items():
            same_tag = existing_tag == imported_tag
            same_description = record.description == imported_description
            if same_tag and same_description:
                return None
            if same_tag or same_description:
                return existing_tag, record
        return None

    def add_or_update_imported(
        self,
        tags: dict[str, TagRecord],
        tag_name: str,
        description: str,
        vessel: str,
        row_data: dict[str, str],
    ) -> None:
        """Adds or updates an imported tag record."""
        if tag_name in tags:
            record = tags[tag_name]
            record.description = description
            record.vessels.add(vessel)
            record.row_data = row_data
            return

        tags[tag_name] = TagRecord(
            tag_name=tag_name,
            description=description,
            vessels={vessel},
            row_data=row_data,
        )

    def add_vessel_to_existing(
        self, tags: dict[str, TagRecord], tag_name: str, vessel: str
    ) -> None:
        """Associates a vessel with an existing tag."""
        if tag_name in tags:
            tags[tag_name].vessels.add(vessel)

    def unique_suffix_name(self, tags: dict[str, TagRecord], base_tag: str) -> str:
        """Builds a unique name based on base tag with numeric suffix."""
        if base_tag not in tags:
            return base_tag

        index = 2
        while f"{base_tag}_{index}" in tags:
            index += 1
        return f"{base_tag}_{index}"
