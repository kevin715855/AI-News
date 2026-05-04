"""JSON exporter for repository summary data."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .base import ExportData, Exporter, ExporterConfig


class JSONExporter(Exporter):
    """Serialize repository summaries as structured UTF-8 JSON."""

    def __init__(self, config: ExporterConfig | None = None) -> None:
        super().__init__(config or ExporterConfig(output_format="json"))

    def export(self, data: ExportData, output_path: str | Path) -> None:
        path = self._prepare_output_path(output_path)
        payload = self.to_payload(data)
        indent = self.config.indent if self.config.pretty else None
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=indent) + "\n",
            encoding=self.config.encoding,
        )

    def to_payload(self, data: ExportData) -> dict[str, Any]:
        payload = asdict(data)
        if not self.config.include_readme:
            payload["readme_content"] = None
        return {
            "repository": {
                "name": data.repo_name,
                "url": data.repo_url,
                "description": data.description,
            },
            "summary": data.summary,
            "readme_content": payload["readme_content"],
            "metadata": payload["metadata"],
            "source_files": payload["source_files"],
        }
