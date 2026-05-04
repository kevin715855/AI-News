from __future__ import annotations

import json
from pathlib import Path

from cli.export import ExportError
from validator.cli import main


FIXTURES = Path(__file__).parents[1] / "fixtures" / "exporter"


def test_markdown_export_workflow_writes_well_formatted_file(tmp_path: Path) -> None:
    output = tmp_path / "digest.md"

    exit_code = main(["export", "markdown", str(FIXTURES / "sample_repo"), "--output", str(output)])

    content = output.read_text(encoding="utf-8")
    assert exit_code == 0
    assert content.startswith("# ai-news-vietnam\n")
    assert "## Tom tat tieng Viet" in content
    assert "tóm tắt tiếng Việt rõ ràng" in content
    assert "| stars | 1280 |" in content
    assert "| language | Python |" in content
    assert "## README da ban dia hoa" in content
    assert "Dự án cung cấp bản tin AI hằng ngày" in content
    assert "- `README.md`" in content


def test_json_export_workflow_writes_parseable_utf8_file(tmp_path: Path) -> None:
    output = tmp_path / "digest.json"

    exit_code = main(["export", "json", str(FIXTURES / "sample_repo"), "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["repository"] == {
        "name": "ai-news-vietnam",
        "url": "https://github.com/example/ai-news-vietnam",
    }
    assert payload["metadata"]["updated_at"] == "2026-05-01T10:30:00Z"
    assert payload["metadata"]["stars"] == 1280
    assert payload["source_files"] == ["README.md", "src/digest.py"]
    assert "tiếng Việt rõ ràng" in payload["summary"]
    assert "Cài đặt" in payload["readme_content"]


def test_batch_export_writes_markdown_and_json_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "exports"

    exit_code = main(["export", "all", str(FIXTURES / "sample_repo"), "--output-dir", str(output_dir)])

    markdown_output = output_dir / "ai-news-vietnam.md"
    json_output = output_dir / "ai-news-vietnam.json"
    assert exit_code == 0
    assert markdown_output.exists()
    assert json_output.exists()
    assert "# ai-news-vietnam" in markdown_output.read_text(encoding="utf-8")
    assert json.loads(json_output.read_text(encoding="utf-8"))["metadata"]["forks"] == 74


def test_export_can_omit_readme_when_requested(tmp_path: Path) -> None:
    markdown_output = tmp_path / "digest.md"
    json_output = tmp_path / "digest.json"

    markdown_exit = main(
        [
            "export",
            "markdown",
            str(FIXTURES / "sample_repo"),
            "--output",
            str(markdown_output),
            "--no-include-readme",
        ]
    )
    json_exit = main(
        [
            "export",
            "json",
            str(FIXTURES / "sample_repo"),
            "--output",
            str(json_output),
            "--no-include-readme",
        ]
    )

    assert markdown_exit == 0
    assert json_exit == 0
    assert "README da ban dia hoa" not in markdown_output.read_text(encoding="utf-8")
    assert "readme_content" not in json.loads(json_output.read_text(encoding="utf-8"))


def test_export_handles_missing_optional_fields(tmp_path: Path) -> None:
    markdown_output = tmp_path / "minimal.md"
    json_output = tmp_path / "minimal.json"

    markdown_exit = main(
        ["export", "markdown", str(FIXTURES / "missing_optional"), "--output", str(markdown_output)]
    )
    json_exit = main(["export", "json", str(FIXTURES / "missing_optional"), "--output", str(json_output)])

    assert markdown_exit == 0
    assert json_exit == 0
    assert "Tóm tắt ngắn bằng tiếng Việt." in markdown_output.read_text(encoding="utf-8")
    assert "README da ban dia hoa" not in markdown_output.read_text(encoding="utf-8")
    assert json.loads(json_output.read_text(encoding="utf-8"))["metadata"] == {}


def test_export_reports_error_for_missing_repo_path(tmp_path: Path, capsys) -> None:
    output = tmp_path / "digest.md"

    exit_code = main(["export", "markdown", str(tmp_path / "missing"), "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Repository path does not exist" in captured.err
    assert not output.exists()


def test_export_reports_error_for_invalid_fixture_json(tmp_path: Path, capsys) -> None:
    output = tmp_path / "digest.json"

    exit_code = main(["export", "json", str(FIXTURES / "invalid_json"), "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid export data JSON" in captured.err
    assert not output.exists()
