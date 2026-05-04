"""Markdown exporter for repository summary data."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .base import ExportData, Exporter, ExporterConfig


class MarkdownExporter(Exporter):
    """Render repository summaries with a Jinja2 Markdown template."""

    def __init__(self, config: ExporterConfig | None = None) -> None:
        super().__init__(config or ExporterConfig(output_format="markdown"))

    def export(self, data: ExportData, output_path: str | Path) -> None:
        path = self._prepare_output_path(output_path)
        path.write_text(self.render(data), encoding=self.config.encoding)

    def render(self, data: ExportData) -> str:
        template = self._load_template()
        rendered = template.render(
            data=data,
            include_readme=self.config.include_readme,
            metadata_items=sorted(data.metadata.items()),
        )
        return rendered.rstrip() + "\n"

    def _load_template(self):
        template_path = Path(self.config.template_path) if self.config.template_path else _default_template_path()
        environment = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        return environment.get_template(template_path.name)


def _default_template_path() -> Path:
    return Path(__file__).resolve().parents[2] / "templates" / "export.md.j2"
