"""Manage pending Proficy export queue with stable change IDs."""

from __future__ import annotations

from models.pending_export import PendingExportChange
from services.address_normalizer import normalize_address


def export_fields_for_compare(row: dict[str, str]) -> dict[str, str]:
    """Extracts Name, Description, and address for export comparison."""
    name = str(row.get("Name", "")).strip().upper()
    description = str(row.get("Description", "")).strip().upper()
    address = ""
    for key in ("IOAddress", "Address", "ADDRESS", "ioaddress"):
        value = str(row.get(key, "")).strip()
        if value:
            address = normalize_address(value)
            break
    return {"Name": name, "Description": description, "Address": address}


def changed_field_labels(
    baseline: dict[str, str] | None, row_data: dict[str, str]
) -> list[str]:
    """Returns human-readable labels for fields that differ from baseline."""
    if baseline is None:
        return ["Name", "Description", "Address"]
    current = export_fields_for_compare(row_data)
    base = export_fields_for_compare(baseline)
    labels: list[str] = []
    if current["Name"] != base["Name"]:
        labels.append("Name")
    if current["Description"] != base["Description"]:
        labels.append("Description")
    if current["Address"] != base["Address"]:
        labels.append("Address")
    return labels or ["(updated)"]


def _export_tag_name(row: dict[str, str]) -> str:
    return str(row.get("Name", "")).strip().upper()


class ExportQueueService:
    """In-memory Proficy export queue keyed by vessel."""

    def __init__(self) -> None:
        self._by_vessel: dict[str, list[PendingExportChange]] = {}

    def _find_entry(self, vessel: str, row_data: dict[str, str]) -> PendingExportChange | None:
        tag_name = _export_tag_name(row_data)
        if not tag_name:
            return None
        vessel_key = vessel.strip().upper() or "GLOBAL"
        for entry in self._by_vessel.get(vessel_key, []):
            if _export_tag_name(entry.row_data) == tag_name:
                return entry
        return None

    def clear(self) -> None:
        self._by_vessel.clear()

    def count(self) -> int:
        return sum(len(items) for items in self._by_vessel.values())

    def vessel_count(self) -> int:
        return len(self._by_vessel)

    def add(
        self,
        vessel: str,
        row_data: dict[str, str],
        baseline: dict[str, str] | None = None,
    ) -> PendingExportChange:
        existing = self._find_entry(vessel, row_data)
        if existing is not None:
            if baseline is not None and existing.baseline is None:
                existing.baseline = dict(baseline)
            existing.row_data = dict(row_data)
            return existing

        entry = PendingExportChange(
            vessel=vessel.strip().upper() or "GLOBAL",
            row_data=dict(row_data),
            baseline=dict(baseline) if baseline else None,
        )
        self._by_vessel.setdefault(entry.vessel, []).append(entry)
        return entry

    def add_if_different(
        self,
        vessel: str,
        original_row: dict[str, str],
        updated_row: dict[str, str],
    ) -> PendingExportChange | None:
        if export_fields_for_compare(original_row) == export_fields_for_compare(
            updated_row
        ):
            return None

        existing = self._find_entry(vessel, updated_row)
        if existing is not None:
            if existing.baseline is None:
                existing.baseline = dict(original_row)
            existing.row_data = dict(updated_row)
            return existing

        return self.add(vessel, updated_row, baseline=original_row)

    def all_entries(self) -> list[PendingExportChange]:
        items: list[PendingExportChange] = []
        for vessel in sorted(self._by_vessel):
            items.extend(self._by_vessel[vessel])
        return items

    def get(self, change_id: str) -> PendingExportChange | None:
        for entries in self._by_vessel.values():
            for entry in entries:
                if entry.change_id == change_id:
                    return entry
        return None

    def remove(self, change_id: str) -> bool:
        for vessel, entries in self._by_vessel.items():
            filtered = [entry for entry in entries if entry.change_id != change_id]
            if len(filtered) != len(entries):
                if filtered:
                    self._by_vessel[vessel] = filtered
                else:
                    del self._by_vessel[vessel]
                return True
        return False

    def update_row(self, change_id: str, row_data: dict[str, str]) -> bool:
        entry = self.get(change_id)
        if entry is None:
            return False
        entry.row_data = dict(row_data)
        return True

    def to_legacy_exports(self) -> dict[str, list[dict[str, object]]]:
        """Format expected by ExportService.write_exports."""
        exports: dict[str, list[dict[str, object]]] = {}
        for entry in self.all_entries():
            exports.setdefault(entry.vessel, []).append({"row": dict(entry.row_data)})
        return exports
