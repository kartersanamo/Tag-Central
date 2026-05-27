"""Cross-program sync policy: Cimplicity wins, Proficy receives exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.tag_record import (
    SYNC_NAME_MISMATCH,
    SYNC_NEEDS_ALIGN,
    SYNC_PROFICY_DRIFT,
    SYNC_PROFICY_ONLY,
    SYNC_SYNCED,
    TagRecord,
)
from services.address_normalizer import addresses_equivalent, normalize_address
from services.cimplicity_review_queue import CimplicityReviewQueue, ReviewQueueItem
from services.tag_link_service import LinkResult, TagLinkService


def normalize_description(text: str) -> str:
    """Canonical descriptions are uppercase for consistency."""
    return " ".join(text.strip().upper().split())


@dataclass
class CimplicityImportRow:
    """Prepared Cimplicity import row for sync processing."""

    pt_id: str
    description: str
    address: str
    row_data: dict[str, str]
    row_index: int


@dataclass
class CimplicitySyncAction:
    """One row requiring user decision during Cimplicity import."""

    row_index: int
    pt_id: str
    cimplicity_description: str
    address: str
    row_data: dict[str, str]
    existing_tag: str
    existing_description: str
    proficy_name: str
    issue: str
    default_action: str = "align_proficy"


@dataclass
class CimplicityImportSummary:
    """Aggregated results from a Cimplicity import pass."""

    total_rows: int = 0
    linked_synced: int = 0
    auto_aligned: int = 0
    review_queue_added: int = 0
    skipped: int = 0
    proficy_exports_queued: int = 0
    manual_cimplicity_flags: int = 0
    actionable: list[CimplicitySyncAction] = field(default_factory=list)


class CrossProgramSyncService:
    """Applies dual-program synchronization policies."""

    def __init__(
        self,
        link_service: TagLinkService | None = None,
        review_queue: CimplicityReviewQueue | None = None,
    ) -> None:
        self._linker = link_service or TagLinkService()
        self._review_queue = review_queue or CimplicityReviewQueue()

    @property
    def review_queue(self) -> CimplicityReviewQueue:
        return self._review_queue

    def prepare_cimplicity_rows(
        self, rows: list[dict[str, str]]
    ) -> list[CimplicityImportRow]:
        prepared: list[CimplicityImportRow] = []
        for index, row in enumerate(rows):
            pt_id = row.get("PT_ID", "").strip().upper()
            if not pt_id:
                continue
            prepared.append(
                CimplicityImportRow(
                    pt_id=pt_id,
                    description=normalize_description(row.get("DESC", "")),
                    address=normalize_address(row.get("ADDR", "")),
                    row_data=dict(row),
                    row_index=index,
                )
            )
        return prepared

    def analyze_cimplicity_import(
        self,
        tags: dict[str, TagRecord],
        rows: list[CimplicityImportRow],
        vessel: str,
    ) -> CimplicityImportSummary:
        """Classifies Cimplicity rows without mutating tags."""
        summary = CimplicityImportSummary(total_rows=len(rows))
        for row in rows:
            link = self._linker.link_cimplicity_row(tags, row.pt_id, row.address)
            if link.ambiguous_tags:
                summary.actionable.append(
                    CimplicitySyncAction(
                        row_index=row.row_index,
                        pt_id=row.pt_id,
                        cimplicity_description=row.description,
                        address=row.address,
                        row_data=row.row_data,
                        existing_tag=link.ambiguous_tags[0],
                        existing_description=tags[link.ambiguous_tags[0]].description,
                        proficy_name=tags[link.ambiguous_tags[0]].proficy_name,
                        issue=f"ambiguous_address:{','.join(link.ambiguous_tags)}",
                        default_action="align_proficy",
                    )
                )
                continue

            if link.canonical_tag is None:
                summary.review_queue_added += 1
                continue

            record = tags[link.canonical_tag]
            issues = self._detect_issues(record, row)
            if not issues:
                summary.linked_synced += 1
                continue

            summary.actionable.append(
                CimplicitySyncAction(
                    row_index=row.row_index,
                    pt_id=row.pt_id,
                    cimplicity_description=row.description,
                    address=row.address,
                    row_data=row.row_data,
                    existing_tag=link.canonical_tag,
                    existing_description=record.description,
                    proficy_name=record.proficy_name or link.canonical_tag,
                    issue="|".join(issues),
                    default_action="align_proficy",
                )
            )
        return summary

    def resolve_tag_key(
        self,
        tags: dict[str, TagRecord],
        row: CimplicityImportRow,
        link: LinkResult,
        preferred_key: str | None = None,
    ) -> str | None:
        """
        Finds the current dict key for a linked row.
        Handles prior renames during the same import batch (stale dialog keys).
        """
        candidates: list[str] = []
        for key in (preferred_key, link.canonical_tag, row.pt_id):
            if key and key not in candidates:
                candidates.append(key)

        for key in candidates:
            if key in tags:
                return key

        for tag_name, record in tags.items():
            if record.cimplicity_pt_id == row.pt_id:
                return tag_name

        if row.address:
            for tag_name, record in tags.items():
                record_address = record.linked_address or TagRecord._address_from_row(
                    record.proficy_row_data
                )
                if addresses_equivalent(record_address, row.address):
                    return tag_name

        if len(link.ambiguous_tags) == 1 and link.ambiguous_tags[0] in tags:
            return link.ambiguous_tags[0]

        return None

    def apply_cimplicity_row(
        self,
        tags: dict[str, TagRecord],
        row: CimplicityImportRow,
        vessel: str,
        action: str,
        canonical_tag: str | None = None,
    ) -> tuple[bool, dict[str, str] | None]:
        """
        Applies one Cimplicity row decision.
        Returns (changed, proficy_export_row or None).
        """
        if action == "skip":
            return False, None

        if action == "flag_manual_cimplicity":
            return False, {
                "PT_ID": row.pt_id,
                "field": "manual_review",
                "current": row.description,
                "recommended": row.description,
                "reason": "User flagged manual Cimplicity change",
            }

        link = self._linker.link_cimplicity_row(tags, row.pt_id, row.address)
        tag_key = self.resolve_tag_key(tags, row, link, preferred_key=canonical_tag)
        if tag_key is None:
            if action == "link_only":
                return False, None
            self._review_queue.add(
                ReviewQueueItem(
                    vessel=vessel,
                    pt_id=row.pt_id,
                    description=row.description,
                    address=row.address,
                    row_data=row.row_data,
                    imported_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            return False, None

        record = tags[tag_key]
        link_method = link.method or "manual"
        record.set_cimplicity_snapshot(row.row_data, vessel, link_method)

        if action == "link_only":
            record.sync_status = SYNC_NEEDS_ALIGN
            return True, None

        export_row = self.align_proficy_to_cimplicity(tags, tag_key, row, vessel)
        return True, export_row

    def align_proficy_to_cimplicity(
        self,
        tags: dict[str, TagRecord],
        canonical_tag: str,
        row: CimplicityImportRow,
        vessel: str,
    ) -> dict[str, str] | None:
        """Updates canonical + Proficy to match Cimplicity; may rename tag key."""
        record = tags[canonical_tag]
        old_export = record.proficy_export_row()
        record.set_cimplicity_snapshot(row.row_data, vessel, record.link_method or "address")

        new_canonical_name = row.pt_id
        new_description = row.description

        needs_rename = canonical_tag != new_canonical_name
        needs_desc = record.description != new_description
        needs_proficy_name = (record.proficy_name or canonical_tag) != new_canonical_name

        record.description = new_description
        record.cimplicity_pt_id = row.pt_id

        if record.proficy_row_data:
            record.proficy_row_data["Name"] = new_canonical_name
            record.proficy_row_data["Description"] = new_description
            if row.address:
                record.proficy_row_data["IOAddress"] = row.address
                record.proficy_row_data["Address"] = row.address
        record.proficy_name = new_canonical_name
        if row.address:
            record.linked_address = row.address

        if needs_rename:
            tags.pop(canonical_tag)
            record.tag_name = new_canonical_name
            tags[new_canonical_name] = record
        else:
            record.tag_name = new_canonical_name

        record.sync_status = SYNC_SYNCED
        new_export = record.proficy_export_row()
        if needs_rename or needs_desc or needs_proficy_name or old_export != new_export:
            return new_export
        return None

    def import_proficy_row(
        self,
        tags: dict[str, TagRecord],
        tag_name: str,
        description: str,
        vessel: str,
        row_data: dict[str, str],
    ) -> str:
        """
        Merges a Proficy import row. Returns sync_status after merge.
        Does not overwrite canonical description when Cimplicity is linked.
        """
        if tag_name in tags:
            record = tags[tag_name]
            record.set_proficy_snapshot(row_data, vessel)
            if record.cimplicity_pt_id or record.cimplicity_row_data:
                cim_desc = normalize_description(
                    record.cimplicity_row_data.get("DESC", record.description)
                )
                if record.description != cim_desc:
                    record.sync_status = SYNC_PROFICY_DRIFT
                elif (record.proficy_name or tag_name) != record.cimplicity_pt_id:
                    record.sync_status = SYNC_NAME_MISMATCH
                else:
                    record.sync_status = SYNC_SYNCED
            else:
                record.description = description
                record.sync_status = SYNC_PROFICY_ONLY
            return record.sync_status

        record = TagRecord(
            tag_name=tag_name,
            description=description,
            vessels={vessel},
            proficy_row_data=dict(row_data),
            proficy_name=tag_name,
            linked_address=normalize_address(TagRecord._address_from_row(row_data)),
            sync_status=SYNC_PROFICY_ONLY,
        )
        tags[tag_name] = record
        return record.sync_status

    def _detect_issues(self, record: TagRecord, row: CimplicityImportRow) -> list[str]:
        issues: list[str] = []
        proficy_name = (record.proficy_name or record.tag_name).strip().upper()
        if proficy_name != row.pt_id and record.tag_name != row.pt_id:
            issues.append("name_mismatch")
        if record.description != row.description:
            issues.append("description_mismatch")
        return issues

    def rename_tag_key(
        self, tags: dict[str, TagRecord], old_key: str, new_key: str
    ) -> None:
        if old_key == new_key:
            return
        record = tags.pop(old_key)
        record.tag_name = new_key
        tags[new_key] = record
