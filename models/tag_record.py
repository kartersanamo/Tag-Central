"""Tag domain model."""

from __future__ import annotations

from dataclasses import dataclass, field

from models.program_snapshot import ProgramSnapshot


SYNC_SYNCED = "synced"
SYNC_PROFICY_ONLY = "proficy_only"
SYNC_PROFICY_DRIFT = "proficy_drift"
SYNC_NAME_MISMATCH = "name_mismatch"
SYNC_NEEDS_ALIGN = "needs_align"


@dataclass(slots=True)
class TagRecord:
    """Represents one canonical tag entry across Proficy and Cimplicity."""

    tag_name: str
    description: str
    vessels: set[str] = field(default_factory=set)
    proficy_row_data: dict[str, str] = field(default_factory=dict)
    cimplicity_row_data: dict[str, str] = field(default_factory=dict)
    cimplicity_pt_id: str = ""
    proficy_name: str = ""
    linked_address: str = ""
    sync_status: str = SYNC_PROFICY_ONLY
    link_method: str | None = None

    @property
    def row_data(self) -> dict[str, str]:
        """Proficy export payload (backward compatible)."""
        return self.proficy_row_data

    @row_data.setter
    def row_data(self, value: dict[str, str]) -> None:
        self.proficy_row_data = dict(value)
        name = value.get("Name", "").strip().upper()
        if name:
            self.proficy_name = name

    @property
    def proficy(self) -> ProgramSnapshot | None:
        if not self.proficy_row_data and not self.proficy_name:
            return None
        from services.address_normalizer import normalize_address

        address = self.linked_address or normalize_address(
            self._address_from_row(self.proficy_row_data)
        )
        return ProgramSnapshot(
            program="proficy",
            tag_id=self.proficy_name or self.tag_name,
            description=self.description,
            address=address,
            row_data=dict(self.proficy_row_data),
            vessel=next(iter(self.vessels), "") if self.vessels else "",
        )

    @property
    def cimplicity(self) -> ProgramSnapshot | None:
        if not self.cimplicity_row_data and not self.cimplicity_pt_id:
            return None
        from services.address_normalizer import normalize_address

        pt_id = self.cimplicity_pt_id or self.cimplicity_row_data.get("PT_ID", "")
        address = normalize_address(self.cimplicity_row_data.get("ADDR", ""))
        desc = self.cimplicity_row_data.get("DESC", self.description)
        return ProgramSnapshot(
            program="cimplicity",
            tag_id=pt_id.strip().upper(),
            description=str(desc).strip().upper(),
            address=address,
            row_data=dict(self.cimplicity_row_data),
            vessel=next(iter(self.vessels), "") if self.vessels else "",
        )

    def set_proficy_snapshot(
        self, row_data: dict[str, str], vessel: str, description: str | None = None
    ) -> None:
        """Updates Proficy-side data from an import row."""
        self.proficy_row_data = dict(row_data)
        self.proficy_name = row_data.get("Name", self.tag_name).strip().upper()
        from services.address_normalizer import is_resolvable_address, normalize_address

        address = normalize_address(self._address_from_row(row_data))
        if is_resolvable_address(address):
            self.linked_address = address
        if description is not None:
            pass  # canonical may be set separately
        if vessel:
            self.vessels.add(vessel.strip().upper())

    def set_cimplicity_snapshot(
        self, row_data: dict[str, str], vessel: str, link_method: str
    ) -> None:
        """Stores Cimplicity import row without mutating canonical fields."""
        self.cimplicity_row_data = dict(row_data)
        self.cimplicity_pt_id = row_data.get("PT_ID", "").strip().upper()
        from services.address_normalizer import normalize_address

        address = normalize_address(row_data.get("ADDR", ""))
        if address:
            self.linked_address = address
        self.link_method = link_method
        if vessel:
            self.vessels.add(vessel.strip().upper())

    def proficy_export_row(self) -> dict[str, str]:
        """Builds a Proficy-shaped row for batch export."""
        row = dict(self.proficy_row_data) if self.proficy_row_data else {}
        row["Name"] = self.tag_name
        row["Description"] = self.description
        if self.linked_address:
            row["IOAddress"] = self.linked_address
            row["Address"] = self.linked_address
        return row

    def vessels_csv(self) -> str:
        """Returns vessels as a deterministic semicolon-delimited string."""
        return ";".join(sorted(self.vessels))

    @staticmethod
    def _address_from_row(row_data: dict[str, str]) -> str:
        for key in ("IOAddress", "Address", "ADDRESS", "ADDR", "address"):
            if key in row_data and str(row_data[key]).strip():
                return str(row_data[key]).strip()
        return ""
