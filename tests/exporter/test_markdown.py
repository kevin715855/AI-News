from pathlib import Path

from exporter import ExportData, ExporterConfig, MarkdownExporter


def _data() -> ExportData:
    return ExportData(
        repo_name="AI-News",
        repo_url="https://github.com/example/AI-News",
        summary="Day la tom tat tieng Viet.",
        readme_content="# AI-News\n\nNoi dung README da duoc Viet hoa.",
        metadata={
            "stars": 42,
            "forks": 7,
            "language": "Python",
            "updated_at": "2026-05-02T00:00:00Z",
        },
        source_files=["README.md", "src/main.py"],
    )


def test_markdown_exporter_writes_formatted_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "export.md"

    MarkdownExporter().export(_data(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# AI-News")
    assert "## Tom tat tieng Viet" in content
    assert "Day la tom tat tieng Viet." in content
    assert "| stars | 42 |" in content
    assert "## README da Viet hoa" in content
    assert "- src/main.py" in content


def test_markdown_exporter_can_exclude_readme(tmp_path: Path) -> None:
    output_path = tmp_path / "export.md"
    exporter = MarkdownExporter(ExporterConfig(include_readme=False))

    exporter.export(_data(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "README da Viet hoa" not in content
    assert "Noi dung README" not in content


def test_markdown_exporter_uses_custom_template(tmp_path: Path) -> None:
    template = tmp_path / "custom.md.j2"
    template.write_text("{{ data.repo_name }} :: {{ data.summary }}", encoding="utf-8")
    output_path = tmp_path / "custom.md"

    MarkdownExporter(ExporterConfig(template_path=template)).export(_data(), output_path)

    assert output_path.read_text(encoding="utf-8") == "AI-News :: Day la tom tat tieng Viet.\n"
