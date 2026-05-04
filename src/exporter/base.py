"""Base data model and interface for repository summary exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import ExportFormat, Metadata, SourceFiles


@dataclass(frozen=True)
class ExportData:
    """Repository summary payload consumed by all exporters."""

    repo_name: str
    repo_url: str
    summary: str
    readme_content: str | None = None
    metadata: Metadata = field(default_factory=dict)
    description: str | None = None
    source_files: SourceFiles = field(default_factory=list)


@dataclass(frozen=True)
class ExporterConfig:
    """Common export settings shared by concrete exporters."""

    output_format: ExportFormat | None = None
    include_readme: bool = True
    pretty: bool = True
    indent: int = 2
    template_path: str | Path | None = None
    encoding: str = "utf-8"


class Exporter(ABC):
    """Abstract base class for custom repository summary exporters."""

    def __init__(self, config: ExporterConfig | None = None) -> None:
        self.config = config or ExporterConfig()

    @abstractmethod
    def export(self, data: ExportData, output_path: str | Path) -> None:
        """Write exported data to output_path."""

    def _prepare_output_path(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _metadata_value(data: ExportData, key: str, default: Any = "") -> Any:
        value = data.metadata.get(key, default)
        return default if value is None else value
