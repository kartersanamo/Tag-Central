"""Tag domain model."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class TagRecord:
    """Represents one canonical tag entry."""

    tag_name: str
    description: str
    vessels: set[str] = field(default_factory=set)
    row_data: dict[str, str] = field(default_factory=dict)

    def vessels_csv(self) -> str:
        """Returns vessels as a deterministic semicolon-delimited string."""
        return ";".join(sorted(self.vessels))
