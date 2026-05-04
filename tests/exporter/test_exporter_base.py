from pathlib import Path

import pytest

from exporter import ExportData, Exporter, ExporterConfig


def test_exporter_is_abstract() -> None:
    with pytest.raises(TypeError):
        Exporter()


def test_export_data_defaults_optional_fields() -> None:
    data = ExportData(
        repo_name="AI-News",
        repo_url="https://github.com/example/AI-News",
        summary="Tom tat tieng Viet",
    )

    assert data.readme_content is None
    assert data.metadata == {}
    assert data.source_files == []


def test_exporter_config_defaults_common_options() -> None:
    config = ExporterConfig()

    assert config.include_readme is True
    assert config.pretty is True
    assert config.indent == 2
    assert config.encoding == "utf-8"


class DummyExporter(Exporter):
    def export(self, data: ExportData, output_path: str | Path) -> None:
        path = self._prepare_output_path(output_path)
        path.write_text(data.summary, encoding=self.config.encoding)


def test_exporter_prepares_parent_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "summary.txt"
    data = ExportData(repo_name="demo", repo_url="", summary="ok")

    DummyExporter().export(data, output_path)

    assert output_path.read_text(encoding="utf-8") == "ok"
