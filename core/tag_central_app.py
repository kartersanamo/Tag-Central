"""Headless facade for Tag Central business operations."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app_config import (
    BULK_DELETE_BACKUP_THRESHOLD,
    EXPORT_FOLDER,
    SYNC_STATUS_LABELS,
)
from app_identity import documentation_dir
from controllers.app_context import AppContext
from core.exceptions import TagCentralError
from core.import_options import ImportOptions
from models.tag_record import (
    SYNC_NAME_MISMATCH,
    SYNC_NEEDS_ALIGN,
    SYNC_PROFICY_DRIFT,
    SYNC_PROFICY_ONLY,
    SYNC_SYNCED,
    TagRecord,
)
from services.address_normalizer import is_resolvable_address, normalize_address
from services.cross_program_sync_service import (
    CimplicityImportRow,
    normalize_description,
)
from services.documentation_service import DOCUMENT_TYPES
from services.export_queue_service import changed_field_labels
from services.find_replace_service import matches_find_scope, preview_replace
from services.internal_mismatch_service import MISMATCH_DUPLICATE_DESCRIPTION
from services.sync_status_labels import sync_status_label
from services.tag_address import extract_address, record_address


class TagCentralApp:
    """Single headless facade owning AppContext and business operations."""

    def __init__(self, ctx: AppContext | None = None) -> None:
        self.ctx = ctx or AppContext.create_headless()

    @classmethod
    def from_context(cls, ctx: AppContext) -> TagCentralApp:
        return cls(ctx)

    # --- Context shortcuts ---

    @property
    def tags(self) -> dict[str, TagRecord]:
        return self.ctx.tags

    @property
    def export_queue(self):
        return self.ctx.export_queue

    @property
    def sync(self):
        return self.ctx.sync

    @property
    def cross_program(self):
        return self.ctx.cross_program

    @property
    def suggester(self):
        return self.ctx.suggester

    @property
    def loader(self):
        return self.ctx.loader

    @property
    def cimplicity_loader(self):
        return self.ctx.cimplicity_loader

    @property
    def proficy_analyzer(self):
        assert self.ctx.proficy_analyzer is not None
        return self.ctx.proficy_analyzer

    @property
    def manual_tasks(self):
        return self.ctx.manual_tasks

    @property
    def merge_service(self):
        return self.ctx.merge_service

    @property
    def backup_service(self):
        return self.ctx.backup_service

    @property
    def export_service(self):
        return self.ctx.export_service

    @property
    def export_validator(self):
        return self.ctx.export_validator

    @property
    def documentation(self):
        assert self.ctx.documentation is not None
        return self.ctx.documentation

    @property
    def cimplicity_report(self):
        return self.ctx.cimplicity_report

    @property
    def repository(self):
        return self.ctx.repository

    @property
    def conflicted_tags(self) -> set[str]:
        return self.ctx.conflicted_tags

    @conflicted_tags.setter
    def conflicted_tags(self, value: set[str]) -> None:
        self.ctx.conflicted_tags = value

    @property
    def tag_mismatch_group_label(self) -> dict[str, str]:
        return self.ctx.tag_mismatch_group_label

    @property
    def tag_mismatch_type(self) -> dict[str, str]:
        return self.ctx.tag_mismatch_type

    @property
    def tag_conflict_peers(self) -> dict[str, list[str]]:
        return self.ctx.tag_conflict_peers

    @property
    def cimplicity_manual_entries(self) -> list[dict[str, str]]:
        return self.ctx.cimplicity_manual_entries

    @property
    def last_cimplicity_link_report(self) -> list[str]:
        return self.ctx.last_cimplicity_link_report

    @last_cimplicity_link_report.setter
    def last_cimplicity_link_report(self, value: list[str]) -> None:
        self.ctx.last_cimplicity_link_report = value

    def persist_tags(self) -> None:
        self.ctx.persist_tags()

    def schedule_persist(self) -> None:
        self.ctx.schedule_persist()

    def recalculate_conflicted_tags(self) -> None:
        result = self.ctx.mismatch_service.calculate(self.tags)
        self.ctx.conflicted_tags = result.conflicted_tags
        self.ctx.tag_conflict_peers = result.peers
        self.ctx.tag_mismatch_group_label = result.group_labels
        self.ctx.tag_mismatch_type = result.mismatch_types

    def queue_change(
        self,
        vessel: str,
        row_data: dict[str, str],
        baseline: dict[str, str] | None = None,
    ) -> None:
        self.export_queue.add(vessel, row_data, baseline=baseline)

    def queue_change_if_different(
        self,
        vessel: str,
        original_row: dict[str, str],
        updated_row: dict[str, str],
    ) -> None:
        self.export_queue.add_if_different(vessel, original_row, updated_row)

    def auto_backup_before_bulk(self, reason: str) -> list[Path]:
        return self.backup_service.create_bulk_operation_backup()

    def reload_tags(self) -> None:
        self.ctx.tags = self.repository.load()
        self.cross_program.review_queue.load()
        self.manual_tasks.load()

    # --- Status ---

    def status(self) -> dict[str, int]:
        return {
            "pending_exports": self.export_queue.count(),
            "export_vessels": self.export_queue.vessel_count(),
            "review_queue": self.cross_program.review_queue.count(),
            "manual_tasks": self.manual_tasks.pending_count(),
            "tags": len(self.tags),
            "internal_mismatches": len(self.conflicted_tags),
        }

    # --- Tag listing ---

    def list_tags(
        self,
        *,
        vessel: str | None = None,
        program: str | None = None,
        search: str | None = None,
        mismatches_only: bool = False,
    ) -> list[dict[str, object]]:
        self.recalculate_conflicted_tags()
        vessel_filter = None if not vessel or vessel.upper() == "ALL" else vessel.upper()
        query = (search or "").strip().lower()
        rows: list[dict[str, object]] = []

        for tag_name, record in self.tags.items():
            if mismatches_only and tag_name not in self.conflicted_tags:
                continue
            if vessel_filter and vessel_filter not in record.vessels:
                continue
            if not self._passes_program_filter(record, program):
                continue
            address_text = record_address(record)
            peers_text = ", ".join(self.tag_conflict_peers.get(tag_name, []))
            searchable = (
                f"{record.tag_name} {record.description} {record.proficy_name} "
                f"{record.cimplicity_pt_id} {address_text} "
                f"{', '.join(sorted(record.vessels))} {peers_text}"
            ).lower()
            if query and query not in searchable:
                continue
            rows.append(self._tag_row_dict(tag_name, record))

        rows.sort(key=lambda item: str(item.get("tag_name", "")).lower())
        return rows

    def show_tag(self, tag_name: str) -> dict[str, object]:
        tag_key = tag_name.strip().upper()
        record = self.tags.get(tag_key)
        if record is None:
            raise TagCentralError(f"Tag not found: {tag_name}")
        return self._tag_row_dict(tag_key, record, detailed=True)

    def tag_diff(self, tag_name: str) -> dict[str, object]:
        tag_key = tag_name.strip().upper()
        record = self.tags.get(tag_key)
        if record is None:
            raise TagCentralError(f"Tag not found: {tag_name}")

        proficy_name = (record.proficy_name or record.tag_name).strip().upper()
        proficy_desc = str(record.proficy_row_data.get("Description", record.description))
        proficy_addr = normalize_address(
            TagRecord._address_from_row(record.proficy_row_data)
        ) or record.linked_address
        cim_name = (record.cimplicity_pt_id or "").strip().upper()
        cim_desc = (
            normalize_description(record.cimplicity_row_data.get("DESC", ""))
            if record.cimplicity_row_data
            else ""
        )
        cim_addr = (
            normalize_address(record.cimplicity_row_data.get("ADDR", ""))
            if record.cimplicity_row_data
            else ""
        )
        sync_label = SYNC_STATUS_LABELS.get(
            record.sync_status, record.sync_status.replace("_", " ").title()
        )

        fields = []
        for field_name, canonical, proficy, cimplicity in (
            ("Tag / Name", record.tag_name, proficy_name, cim_name or "—"),
            ("Description", record.description, proficy_desc, cim_desc or "—"),
            ("Address", record.linked_address or "—", proficy_addr or "—", cim_addr or "—"),
            ("Sync", sync_label, "—", "—"),
        ):
            differs = len({canonical, proficy, cimplicity} - {"—"}) > 1
            fields.append(
                {
                    "field": field_name,
                    "canonical": canonical,
                    "proficy": proficy,
                    "cimplicity": cimplicity,
                    "differs": differs and field_name != "Sync",
                }
            )
        return {"tag_name": tag_key, "fields": fields}

    def _tag_row_dict(
        self, tag_name: str, record: TagRecord, *, detailed: bool = False
    ) -> dict[str, object]:
        row: dict[str, object] = {
            "tag_name": record.tag_name,
            "proficy_name": record.proficy_name or "",
            "cimplicity_pt_id": record.cimplicity_pt_id or "",
            "description": record.description,
            "address": record_address(record),
            "sync_status": record.sync_status,
            "sync_label": sync_status_label(record.sync_status),
            "vessels": sorted(record.vessels),
            "conflict_group": self.tag_mismatch_group_label.get(tag_name, ""),
            "conflict_peers": self.tag_conflict_peers.get(tag_name, []),
        }
        if detailed:
            row["proficy_row_data"] = dict(record.proficy_row_data)
            row["cimplicity_row_data"] = dict(record.cimplicity_row_data)
        return row

    @staticmethod
    def _passes_program_filter(record: TagRecord, program: str | None) -> bool:
        program_filter = (program or "ALL").strip()
        if program_filter in {"", "ALL"}:
            return True
        if program_filter.lower() in {"proficy", "proficy only", "proficy_only"}:
            return bool(record.proficy_row_data) and not record.cimplicity_pt_id
        if program_filter.lower() in {"cimplicity", "cimplicity only", "cimplicity_only"}:
            return bool(record.cimplicity_pt_id or record.cimplicity_row_data)
        if program_filter.lower() in {"needs_sync", "needs sync", "needs-sync"}:
            return record.sync_status in {
                SYNC_PROFICY_DRIFT,
                SYNC_NEEDS_ALIGN,
                SYNC_NAME_MISMATCH,
            }
        return True

    # --- Tag mutations ---

    def add_tag(
        self,
        *,
        tag_name: str,
        description: str,
        address: str = "",
        vessels: set[str] | None = None,
        program: str = "both",
        queue_proficy: bool = True,
    ) -> dict[str, object]:
        tag_name = tag_name.strip().upper()
        description = description.strip().upper()
        address = address.strip().upper()
        vessels = vessels or {"GLOBAL"}
        program = program.strip().lower()

        if not tag_name:
            raise TagCentralError("Tag name cannot be empty.")
        if not description:
            raise TagCentralError("Description cannot be empty.")
        if tag_name in self.tags:
            raise TagCentralError(f"Tag already exists: {tag_name}")
        if program not in {"proficy", "cimplicity", "both"}:
            raise TagCentralError("Program must be proficy, cimplicity, or both.")

        record = TagRecord(tag_name=tag_name, description=description, vessels=set(vessels))
        if address and is_resolvable_address(address):
            record.linked_address = normalize_address(address)

        if program in {"proficy", "both"}:
            row_data = {"Name": tag_name, "Description": description}
            if address:
                row_data["IOAddress"] = address
                row_data["Address"] = address
            record.set_proficy_snapshot(row_data, next(iter(vessels), "GLOBAL"))
            record.sync_status = SYNC_PROFICY_ONLY

        if program in {"cimplicity", "both"}:
            cim_row = {"PT_ID": tag_name, "DESC": description}
            if address:
                cim_row["ADDR"] = address
            record.set_cimplicity_snapshot(cim_row, next(iter(vessels), "GLOBAL"), "manual")
            record.cimplicity_pt_id = tag_name
            record.sync_status = SYNC_SYNCED if program == "both" else SYNC_NEEDS_ALIGN

        self.tags[tag_name] = record
        self.persist_tags()

        if queue_proficy and program in {"proficy", "both"}:
            export_row = record.proficy_export_row()
            for vessel in vessels:
                self.queue_change(vessel=vessel, row_data=export_row)

        return self.show_tag(tag_name)

    def edit_tag(
        self,
        old_tag: str,
        *,
        tag_name: str | None = None,
        description: str | None = None,
        address: str | None = None,
        vessels: set[str] | None = None,
    ) -> dict[str, object]:
        old_key = old_tag.strip().upper()
        record = self.tags.get(old_key)
        if record is None:
            raise TagCentralError(f"Tag not found: {old_tag}")

        old_description = record.description
        old_address = extract_address(record.row_data)
        old_vessels = set(record.vessels)
        old_row_data = dict(record.row_data)
        old_sync_status = record.sync_status
        old_cimplicity_pt_id = record.cimplicity_pt_id

        new_tag = (tag_name if tag_name is not None else record.tag_name).strip().upper()
        new_description = (
            description if description is not None else record.description
        ).strip().upper()
        new_address = (address if address is not None else old_address).strip().upper()
        new_vessels = vessels if vessels is not None else set(record.vessels)

        if not new_tag:
            raise TagCentralError("Tag name cannot be empty.")
        if not new_description:
            raise TagCentralError("Description cannot be empty.")
        if new_tag in self.tags and new_tag != old_key:
            raise TagCentralError(f"Tag already exists: {new_tag}")

        self.tags.pop(old_key)
        record.tag_name = new_tag
        record.description = new_description
        record.vessels = new_vessels
        self.tags[new_tag] = record
        if old_key in self.conflicted_tags:
            self.conflicted_tags.discard(old_key)
            self.conflicted_tags.add(new_tag)

        has_changed = (
            old_key != new_tag
            or old_description != new_description
            or old_address != new_address
            or old_vessels != new_vessels
        )
        record.proficy_row_data["Address"] = new_address
        record.proficy_row_data["IOAddress"] = new_address
        record.proficy_name = new_tag
        if is_resolvable_address(new_address):
            record.linked_address = normalize_address(new_address)
        elif not record.cimplicity_pt_id:
            record.linked_address = ""
        if record.cimplicity_pt_id:
            if record.description != normalize_description(
                record.cimplicity_row_data.get("DESC", record.description)
            ):
                record.sync_status = SYNC_PROFICY_DRIFT
            else:
                record.sync_status = SYNC_SYNCED

        if has_changed:
            target_vessels = new_vessels or old_vessels or {"GLOBAL"}
            updated_row = record.proficy_export_row()
            for vessel in target_vessels:
                self.queue_change(vessel=vessel, row_data=updated_row)

        if old_sync_status == SYNC_SYNCED and old_cimplicity_pt_id:
            task_vessel = next(iter(new_vessels or old_vessels or {"GLOBAL"}))
            if old_key != new_tag:
                self.manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="tag_name",
                    old_value=old_key,
                    new_value=new_tag,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )
            if old_description != new_description:
                self.manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="description",
                    old_value=old_description,
                    new_value=new_description,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )
            if old_address != new_address:
                self.manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="address",
                    old_value=old_address,
                    new_value=new_address,
                    reason="Manual edit on synced tag requires Cimplicity update",
                )

        self.persist_tags()
        return self.show_tag(new_tag)

    def delete_tags(self, tag_names: list[str], *, auto_backup: bool = True) -> int:
        names = [name.strip().upper() for name in tag_names if name.strip()]
        if not names:
            raise TagCentralError("No tags specified.")
        if auto_backup and len(names) >= BULK_DELETE_BACKUP_THRESHOLD:
            self.auto_backup_before_bulk("delete_tags")

        deleted = 0
        for tag_name in names:
            record = self.tags.pop(tag_name, None)
            if record is None:
                continue
            vessels = record.vessels or {"GLOBAL"}
            deleted_row = dict(record.row_data)
            deleted_row["Name"] = ""
            deleted_row["Description"] = record.description
            for vessel in vessels:
                self.queue_change(vessel=vessel, row_data=deleted_row)
            self.conflicted_tags.discard(tag_name)
            self.tag_conflict_peers.pop(tag_name, None)
            self.tag_mismatch_group_label.pop(tag_name, None)
            self.tag_mismatch_type.pop(tag_name, None)
            deleted += 1

        self.persist_tags()
        self.recalculate_conflicted_tags()
        return deleted

    def merge_tags(self, tag_a: str, tag_b: str, survivor: str) -> dict[str, object]:
        tag_a = tag_a.strip().upper()
        tag_b = tag_b.strip().upper()
        survivor = survivor.strip().upper()
        if survivor not in {tag_a, tag_b}:
            raise TagCentralError("Survivor must be one of the two tags.")
        secondary = tag_b if survivor == tag_a else tag_a
        try:
            record = self.merge_service.merge_tags(self.tags, survivor, secondary)
        except KeyError as error:
            raise TagCentralError(str(error)) from error
        export_row = record.proficy_export_row()
        for vessel in record.vessels or {"GLOBAL"}:
            self.queue_change(vessel=vessel, row_data=export_row)
        self.persist_tags()
        self.recalculate_conflicted_tags()
        return self.show_tag(survivor)

    def align_tags(self, tag_names: list[str]) -> int:
        aligned = 0
        for tag_name in tag_names:
            tag_key = tag_name.strip().upper()
            record = self.tags.get(tag_key)
            if record is None or not record.cimplicity_row_data:
                continue
            row = CimplicityImportRow(
                pt_id=record.cimplicity_pt_id or tag_key,
                description=normalize_description(record.cimplicity_row_data.get("DESC", "")),
                address=record.linked_address,
                row_data=dict(record.cimplicity_row_data),
                row_index=0,
            )
            export_row = self.cross_program.align_proficy_to_cimplicity(
                self.tags, tag_key, row, next(iter(record.vessels), "GLOBAL")
            )
            if export_row:
                for vessel in record.vessels or {"GLOBAL"}:
                    self.queue_change(vessel=vessel, row_data=export_row)
            aligned += 1
        self.persist_tags()
        return aligned

    def increment_descriptions(self, tag_names: list[str]) -> int:
        self.recalculate_conflicted_tags()
        names = [n.strip().upper() for n in tag_names]
        if len(names) < 2:
            raise TagCentralError("Select at least two tags.")

        group_labels: set[str] = set()
        for tag_name in names:
            if self.tag_mismatch_type.get(tag_name) != MISMATCH_DUPLICATE_DESCRIPTION:
                raise TagCentralError(
                    "All tags must be in the same duplicate-description mismatch group."
                )
            label = self.tag_mismatch_group_label.get(tag_name)
            if not label or not label.startswith("G"):
                raise TagCentralError("Invalid mismatch group.")
            group_labels.add(label)
        if len(group_labels) != 1:
            raise TagCentralError("Tags must share one mismatch group.")

        sorted_tags = sorted(names)
        first_record = self.tags[sorted_tags[0]]
        base_description = re.sub(r" \d+$", "", first_record.description.strip().upper())
        if not base_description:
            raise TagCentralError("Cannot increment empty descriptions.")

        updated = 0
        for index, tag_name in enumerate(sorted_tags, start=1):
            record = self.tags.get(tag_name)
            if record is None:
                continue
            old_description = record.description
            old_sync_status = record.sync_status
            old_cimplicity_pt_id = record.cimplicity_pt_id
            new_description = f"{base_description} {index}"
            if old_description == new_description:
                continue

            record.description = new_description
            if record.proficy_row_data:
                record.proficy_row_data["Description"] = new_description

            if record.cimplicity_pt_id:
                cim_desc = normalize_description(
                    record.cimplicity_row_data.get("DESC", record.description)
                )
                if record.description != cim_desc:
                    record.sync_status = SYNC_PROFICY_DRIFT
                elif (record.proficy_name or tag_name) != record.cimplicity_pt_id:
                    record.sync_status = SYNC_NAME_MISMATCH
                else:
                    record.sync_status = SYNC_SYNCED

            target_vessels = record.vessels or {"GLOBAL"}
            export_row = record.proficy_export_row()
            for vessel in target_vessels:
                self.queue_change(vessel=vessel, row_data=export_row)

            if old_sync_status == SYNC_SYNCED and old_cimplicity_pt_id:
                task_vessel = next(iter(target_vessels))
                self.manual_tasks.add_task(
                    vessel=task_vessel,
                    tag_name=old_cimplicity_pt_id,
                    field="description",
                    old_value=old_description,
                    new_value=new_description,
                    reason="Numbered descriptions for internal mismatch resolution",
                )
            updated += 1

        if updated:
            self.persist_tags()
            self.recalculate_conflicted_tags()
        return updated

    def copy_tags(self, tag_names: list[str]) -> str:
        headers = [
            "Tag",
            "Proficy Name",
            "Cimplicity PT_ID",
            "Description",
            "Address",
            "Sync",
            "Group",
            "Vessels",
        ]
        lines = ["\t".join(headers)]
        for tag_name in sorted(tag_names):
            tag_key = tag_name.strip().upper()
            record = self.tags.get(tag_key)
            if record is None:
                continue
            group_label = self.tag_mismatch_group_label.get(tag_key, "")
            values = [
                record.tag_name,
                record.proficy_name or "",
                record.cimplicity_pt_id or "",
                record.description,
                record_address(record),
                sync_status_label(record.sync_status),
                group_label,
                ", ".join(sorted(record.vessels)),
            ]
            lines.append("\t".join(values))
        return "\n".join(lines)

    # --- Find & replace ---

    def find_replace_preview(
        self, find_text: str, replace_text: str, scope: str
    ) -> dict[str, object]:
        if not find_text.strip():
            raise TagCentralError("Find text cannot be empty.")
        pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)
        _, change_count = self._build_find_replace_preview(pattern, replace_text, scope)
        return {"change_count": change_count, "find": find_text, "scope": scope}

    def find_replace_apply(
        self, find_text: str, replace_text: str, scope: str
    ) -> int:
        if not find_text.strip():
            raise TagCentralError("Find text cannot be empty.")
        pattern = re.compile(re.escape(find_text), flags=re.IGNORECASE)
        changed = 0
        for tag_name in list(self.tags.keys()):
            record = self.tags[tag_name]
            old_tag_name = record.tag_name
            old_description = record.description
            old_vessels = set(record.vessels)
            old_row_data = dict(record.row_data)

            new_tag_name = old_tag_name
            new_description = old_description
            if scope in {"tag", "both"}:
                new_tag_name = pattern.sub(replace_text.upper(), old_tag_name).strip().upper()
            if scope in {"description", "both"}:
                new_description = pattern.sub(
                    replace_text.upper(), old_description
                ).strip().upper()

            if new_tag_name == old_tag_name and new_description == old_description:
                continue
            if not new_tag_name or not new_description:
                continue
            if new_tag_name != old_tag_name and new_tag_name in self.tags:
                continue

            self.tags.pop(old_tag_name)
            record.tag_name = new_tag_name
            record.description = new_description
            if new_tag_name != old_tag_name:
                record.proficy_name = new_tag_name
            if record.proficy_row_data:
                record.proficy_row_data["Name"] = new_tag_name
                record.proficy_row_data["Description"] = new_description
            self.tags[new_tag_name] = record

            if old_tag_name in self.conflicted_tags:
                self.conflicted_tags.discard(old_tag_name)
                self.conflicted_tags.add(new_tag_name)

            updated_row = dict(old_row_data)
            updated_row["Name"] = new_tag_name
            updated_row["Description"] = new_description
            for vessel in old_vessels or {"GLOBAL"}:
                self.queue_change(vessel=vessel, row_data=updated_row)
            changed += 1

        if changed:
            self.schedule_persist()
        return changed

    def find_replace_delete(self, find_text: str, scope: str) -> int:
        matching = [
            tag_name
            for tag_name, record in self.tags.items()
            if matches_find_scope(record, find_text, scope)
        ]
        if not matching:
            return 0
        return self.delete_tags(matching)

    def _build_find_replace_preview(
        self, pattern: re.Pattern[str], replace_text: str, scope: str
    ) -> tuple[dict[str, tuple[str, str]], int]:
        preview_map: dict[str, tuple[str, str]] = {}
        if not replace_text:
            for tag_name, record in self.tags.items():
                preview_map[tag_name] = (record.tag_name, record.description)
            return preview_map, 0

        taken_tags = set(self.tags.keys())
        changed_count = 0
        for tag_name in list(self.tags.keys()):
            record = self.tags[tag_name]
            old_tag_name = record.tag_name
            old_description = record.description
            new_tag_name = old_tag_name
            new_description = old_description

            if scope in {"tag", "both"}:
                new_tag_name = preview_replace(old_tag_name, pattern, replace_text)
            if scope in {"description", "both"}:
                new_description = preview_replace(old_description, pattern, replace_text)

            valid = bool(new_tag_name and new_description)
            if valid and new_tag_name != old_tag_name and new_tag_name in taken_tags:
                valid = False

            if valid and (
                new_tag_name != old_tag_name or new_description != old_description
            ):
                changed_count += 1
                if new_tag_name != old_tag_name:
                    taken_tags.discard(old_tag_name)
                    taken_tags.add(new_tag_name)
                preview_map[tag_name] = (new_tag_name, new_description)
            else:
                preview_map[tag_name] = (old_tag_name, old_description)

        return preview_map, changed_count

    # --- Import ---

    def import_proficy(
        self, file_path: str, vessel: str, options: ImportOptions
    ) -> dict[str, object]:
        from core.import_proficy import run_proficy_import

        return run_proficy_import(self, file_path, vessel, options)

    def import_cimplicity(
        self, file_path: str, vessel: str, options: ImportOptions
    ) -> dict[str, object]:
        from core.import_cimplicity import run_cimplicity_import

        return run_cimplicity_import(self, file_path, vessel, options)

    # --- Export ---

    def export_queue_list(self) -> list[dict[str, object]]:
        items = []
        for entry in self.export_queue.all_entries():
            items.append(
                {
                    "change_id": entry.change_id,
                    "vessel": entry.vessel,
                    "name": entry.row_data.get("Name", ""),
                    "description": entry.row_data.get("Description", ""),
                    "address": entry.row_data.get(
                        "IOAddress", entry.row_data.get("Address", "")
                    ),
                    "changed_fields": changed_field_labels(
                        entry.baseline, entry.row_data
                    ),
                }
            )
        return items

    def export_queue_remove(self, change_id: str) -> bool:
        if not self.export_queue.remove(change_id):
            raise TagCentralError(f"Export queue entry not found: {change_id}")
        return True

    def export_queue_edit(
        self,
        change_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        address: str | None = None,
    ) -> dict[str, object]:
        entry = self.export_queue.get(change_id)
        if entry is None:
            raise TagCentralError(f"Export queue entry not found: {change_id}")
        row_data = dict(entry.row_data)
        if name is not None:
            row_data["Name"] = name.strip().upper()
        if description is not None:
            row_data["Description"] = description.strip().upper()
        if address is not None:
            addr = address.strip().upper()
            row_data["IOAddress"] = addr
            row_data["Address"] = addr
        self.export_queue.update_row(change_id, row_data)
        return {
            "change_id": change_id,
            "vessel": entry.vessel,
            "row_data": row_data,
        }

    def export_run(self, *, validate: bool = False) -> dict[str, object]:
        if self.export_queue.count() == 0:
            raise TagCentralError("No pending changes to export.")

        snapshot = self.export_queue.all_entries()
        exports = self.export_queue.to_legacy_exports()
        written_paths = self.export_service.write_exports(exports)
        if not written_paths:
            raise TagCentralError(
                f"No export files were written. Check folder: {EXPORT_FOLDER}"
            )
        self.export_queue.clear()

        result: dict[str, object] = {
            "exported_rows": len(snapshot),
            "files": [str(path) for path in written_paths],
            "export_folder": str(EXPORT_FOLDER),
        }

        if validate:
            result["validation"] = self.export_validate_files(
                [str(path) for path in written_paths], snapshot
            )
        return result

    def export_validate(
        self, file_path: str, vessel: str
    ) -> dict[str, object]:
        path = Path(file_path)
        if not path.exists():
            raise TagCentralError(f"File not found: {file_path}")
        vessel_key = vessel.strip().upper()
        expected = [
            dict(entry.row_data)
            for entry in self.export_queue.all_entries()
            if entry.vessel == vessel_key
        ]
        validation = self.export_validator.validate_export_file(path, expected)
        return {
            "path": str(path),
            "expected_count": validation.expected_count,
            "found_count": validation.found_count,
            "missing": validation.missing,
            "field_mismatches": validation.field_mismatches,
            "ok": not validation.missing and not validation.field_mismatches,
        }

    def export_validate_files(
        self, paths: list[str], expected_entries: list
    ) -> list[dict[str, object]]:
        from models.pending_export import PendingExportChange

        by_vessel: dict[str, list[dict[str, str]]] = {}
        for entry in expected_entries:
            assert isinstance(entry, PendingExportChange)
            by_vessel.setdefault(entry.vessel, []).append(dict(entry.row_data))

        results = []
        for path_str in paths:
            path = Path(path_str)
            vessel_key = path.name.split("_BATCH_EXPORT")[0]
            expected_rows = by_vessel.get(vessel_key, [])
            validation = self.export_validator.validate_export_file(path, expected_rows)
            results.append(
                {
                    "path": str(path),
                    "expected_count": validation.expected_count,
                    "found_count": validation.found_count,
                    "missing": validation.missing,
                    "field_mismatches": validation.field_mismatches,
                    "ok": not validation.missing and not validation.field_mismatches,
                }
            )
        return results

    # --- Backup ---

    def backup_list(self) -> list[dict[str, object]]:
        backups = []
        for item in self.backup_service.list_backups():
            backups.append(
                {
                    "name": item["name"],
                    "modified": item["modified"],
                    "size_kb": item["size_kb"],
                    "rows": item["rows"],
                }
            )
        return backups

    def backup_create(self, prefix: str = "backup") -> str | None:
        path = self.backup_service.create_backup_from_database(prefix=prefix)
        return str(path) if path else None

    def backup_restore(self, backup_name: str) -> None:
        self.persist_tags()
        self.backup_service.create_preload_backup()
        self.backup_service.restore_backup(backup_name)
        self.reload_tags()
        self.recalculate_conflicted_tags()

    def backup_delete(self, backup_name: str) -> None:
        self.backup_service.delete_backup(backup_name)

    def backup_revert(self) -> bool:
        if not self.backup_service.restore_preload_backup():
            raise TagCentralError("No preload backup available to revert.")
        self.reload_tags()
        self.recalculate_conflicted_tags()
        return True

    # --- Documentation ---

    def docs_generate(
        self,
        *,
        doc_types: list[str] | None = None,
        formats: list[str] | None = None,
        vessel: str = "ALL",
    ) -> dict[str, object]:
        selected_types = doc_types or list(DOCUMENT_TYPES.keys())
        format_set = {item.lower() for item in (formats or ["html"])}
        vessel_name = vessel.strip().upper() or "ALL"
        vessel_filter = None if vessel_name == "ALL" else vessel_name

        tables = self.documentation.build_tables(
            self.tags,
            selected_types=selected_types,
            vessel_filter=vessel_filter,
            pending_exports=self.export_queue.all_entries(),
        )
        if not tables:
            raise TagCentralError("No tables generated for the selected options.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = documentation_dir() / f"TagCentral_{timestamp}"
        package = self.documentation.write_package(
            tables,
            output_dir,
            write_html="html" in format_set,
            write_excel="excel" in format_set,
            write_csv="csv" in format_set,
            write_word="word" in format_set,
            vessel_filter=vessel_name,
            tag_count=len(self.tags),
        )
        return {
            "output_dir": str(output_dir),
            "sections": len(tables),
            "written_files": [str(path) for path in package.written_files],
            "index_html": str(output_dir / "index.html"),
        }

    # --- Cimplicity review ---

    def cimplicity_review_list(self) -> list[dict[str, object]]:
        return [
            {
                "vessel": item.vessel,
                "pt_id": item.pt_id,
                "description": item.description,
                "address": item.address,
                "imported_at": item.imported_at,
            }
            for item in self.cross_program.review_queue.items
        ]

    def cimplicity_review_create_proficy(
        self, items: list[tuple[str, str]] | None = None, *, all_items: bool = False
    ) -> dict[str, int]:
        from models.review_queue_item import ReviewQueueItem

        if all_items:
            queue_items = list(self.cross_program.review_queue.items)
        elif items:
            key_set = {(v.strip().upper(), p.strip().upper()) for v, p in items}
            queue_items = [
                item
                for item in self.cross_program.review_queue.items
                if (item.vessel, item.pt_id) in key_set
            ]
        else:
            raise TagCentralError("Specify review items or use --all.")

        if len(queue_items) >= BULK_DELETE_BACKUP_THRESHOLD:
            self.auto_backup_before_bulk("cimplicity_review_create")

        created = 0
        skipped = 0
        remove_keys: list[tuple[str, str]] = []

        for item in queue_items:
            if not isinstance(item, ReviewQueueItem):
                continue
            remove_keys.append((item.vessel, item.pt_id))
            if item.pt_id in self.tags:
                skipped += 1
                continue

            row_data = {
                "Name": item.pt_id,
                "Description": item.description,
                "IOAddress": item.address,
                "Address": item.address,
            }
            self.cross_program.import_proficy_row(
                self.tags,
                tag_name=item.pt_id,
                description=item.description,
                vessel=item.vessel,
                row_data=row_data,
            )
            record = self.tags[item.pt_id]
            record.set_cimplicity_snapshot(item.row_data, item.vessel, "manual")
            record.cimplicity_pt_id = item.pt_id
            record.sync_status = SYNC_SYNCED
            export_row = record.proficy_export_row()
            for vessel in record.vessels or {item.vessel}:
                self.queue_change(vessel=vessel, row_data=export_row)
            created += 1

        if remove_keys:
            self.cross_program.review_queue.remove_many(remove_keys)
        if created:
            self.persist_tags()
        return {"created": created, "skipped": skipped}

    def cimplicity_review_dismiss(
        self, items: list[tuple[str, str]] | None = None, *, all_items: bool = False
    ) -> int:
        if all_items:
            keys = [(item.vessel, item.pt_id) for item in self.cross_program.review_queue.items]
        elif items:
            keys = [(v.strip().upper(), p.strip().upper()) for v, p in items]
        else:
            raise TagCentralError("Specify review items or use --all.")

        if len(keys) >= BULK_DELETE_BACKUP_THRESHOLD:
            self.auto_backup_before_bulk("cimplicity_review_dismiss")
        return self.cross_program.review_queue.remove_many(keys)

    # --- Cimplicity tasks ---

    def cimplicity_tasks_list(self) -> list[dict[str, object]]:
        return [
            {
                "task_id": item.task_id,
                "vessel": item.vessel,
                "tag_name": item.tag_name,
                "field": item.field,
                "old_value": item.old_value,
                "new_value": item.new_value,
                "reason": item.reason,
                "done": item.done,
            }
            for item in self.manual_tasks.items
        ]

    def cimplicity_tasks_toggle(self, task_id: str, done: bool) -> None:
        found = False
        for item in self.manual_tasks.items:
            if item.task_id == task_id:
                found = True
                break
        if not found:
            raise TagCentralError(f"Task not found: {task_id}")
        self.manual_tasks.set_done(task_id, done)

    def cimplicity_tasks_clear_done(self) -> int:
        return self.manual_tasks.clear_done()
