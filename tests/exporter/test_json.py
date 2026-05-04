import json
from pathlib import Path

from exporter import ExportData, ExporterConfig, JSONExporter


def test_json_exporter_writes_structured_utf8_json(tmp_path: Path) -> None:
    data = ExportData(
        repo_name="AI-News",
        repo_url="https://github.com/example/AI-News",
        summary="Tóm tắt tiếng Việt",
        readme_content="# AI-News\n\nNội dung README.",
        metadata={"stars": 10, "forks": 2, "language": "Python"},
        description="Vietnamese digest",
        source_files=["README.md"],
    )
    output_path = tmp_path / "export.json"

    JSONExporter().export(data, output_path)

    content = output_path.read_text(encoding="utf-8")
    payload = json.loads(content)
    assert payload["repository"] == {
        "name": "AI-News",
        "url": "https://github.com/example/AI-News",
        "description": "Vietnamese digest",
    }
    assert payload["summary"] == "Tóm tắt tiếng Việt"
    assert payload["readme_content"] == "# AI-News\n\nNội dung README."
    assert payload["metadata"]["stars"] == 10
    assert payload["source_files"] == ["README.md"]
    assert "\n  " in content


def test_json_exporter_can_exclude_readme(tmp_path: Path) -> None:
    data = ExportData(
        repo_name="AI-News",
        repo_url="",
        summary="summary",
        readme_content="readme",
    )
    output_path = tmp_path / "export.json"

    JSONExporter(ExporterConfig(include_readme=False)).export(data, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8"))["readme_content"] is None
