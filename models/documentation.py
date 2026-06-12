"""Documentation export table models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DocumentationColumn:
    """One column in a generated table."""

    key: str
    header: str


@dataclass
class DocumentationTable:
    """Tabular document section."""

    doc_id: str
    title: str
    summary: str
    columns: list[DocumentationColumn]
    rows: list[dict[str, str]] = field(default_factory=list)


@dataclass
class DocumentationPackageResult:
    """Paths written by a documentation export run."""

    output_dir: Path
    written_files: list[Path] = field(default_factory=list)
